#!/usr/bin/env python
# coding: utf-8

# # Import pre-cleaned data

# The raw data file 'LLCP2017.XPT' includes over 300 variables, mostly intermediate or in a form that cannot be directy analyzed. Interpretting variable names requires referencing the provided codebook ('codebook17_llcp-v2-508.pdf'). The python file 'data_import.py' converts this raw file to a properly formatted and usable analytic dataframe (andf). It also contains the raw file as a pandas dataframe (cdcdf_full), a dictionary of values for categorical variables (value_dict, extracted in a messy-but-workable fashion from the codebook pdf), a dictionary of variables and corresponding questions (v_and_q_dict), and a text string that summarizes the preprocessing steps executed in the data_import.py file (data_description). 

# In[60]:


import numpy as np
import pandas as pd
import pickle
from sklearn.preprocessing import StandardScaler
from sklearn.preprocessing import OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix, classification_report
from sklearn.model_selection import RepeatedStratifiedKFold
from sklearn.model_selection import RandomizedSearchCV
from sklearn.metrics import make_scorer
from sklearn.svm import SVC
from xgboost import XGBClassifier
import xgboost as xgb
from xgboost import plot_importance
from matplotlib import pyplot as plt

# Helps with quick ID of variables
def search_string(x, only_andf=True):
    if only_andf:
        output =  [(i, v_and_q_dict[i]) for i in v_and_q_dict      if x.lower() in v_and_q_dict[i].lower() and i in andf.columns]
    if not only_andf:
        output = [(i, v_and_q_dict[i]) for i in v_and_q_dict                 if x.lower() in v_and_q_dict[i].lower()]
    return output

# Get column names after onehot for cats
def get_names(varlist,cats):
    output = [[m+str(n)              for m,n in zip([varlist[i]+'_']*len(cats[i]),
                            cats[i])] for i in range(len(varlist))]
    return [i for j in output for i in j]


# In[61]:


# Read in data_import dict generated from data_import.py 
data_import = pickle.load( open( "data_import.pickle", "rb" ) )

# State ranks if necessary
state_ranks = pickle.load( open( "state_ranks.pickle", "rb" ) )

# Get andf, v_and_q_dict, and value_dict
andf = data_import['andf']
v_and_q_dict = data_import['v_and_q_dict']
value_dict = data_import['value_dict']

# # Re-attach state, then output csv for MLM in R
# pd.concat([data_import['cdcdf_full']['_STATE'],
#           andf],axis=1).to_csv('andf.csv')
andf['_STATE'] = data_import['cdcdf_full']['_STATE']


# # DV, train/val/test, impute/standardize

# In[62]:


# Drop > 20% missing by row
propmiss = andf.apply(lambda x: sum(x.isna())/len(x), axis=1)
andf = andf.loc[propmiss<.2,:].copy()

# DV prep, drop nan from '_RFHYPE5_Yes 18' (ever been told high bp)
andf = andf.loc[~andf['_RFHYPE5_Yes 18'].isna(),:].copy()
# Reset index
andf.reset_index(drop=True,inplace=True)

# Train/Val/Test Split: 80/20 Train/Val - Test, 80/20 Train - Val
xtv, x_test, ytv, y_test = train_test_split(andf.drop('_RFHYPE5_Yes 18',
                                                     axis=1),
                                           andf['_RFHYPE5_Yes 18'],
                                           test_size=.2,
                                            random_state=1234)
x_train, x_val, y_train, y_val = train_test_split(xtv.copy(),
                                                 ytv.copy(),
                                                 test_size=.2,
                                                 random_state=1234)


# In[63]:


pd.DataFrame({'std':x_train['_STATE'].std(ddof=0),
              'mean':x_train['_STATE'].mean()},
             index=[0]).to_csv('statemsd.csv')


# In[64]:


# Impute, standardize, and onehot (impute/stand not necessary for XGBoost,
# but will be used for comparison models) for objects (cats) and dummies 
# (value_count length == 2)
# For cats/dummies: mode
# For continous (inc. ordinal): mean
# Get vars for cat/dum, continuous, cats, and dums
catdums = [i for i in x_train if len(x_train[i].value_counts())==2            or x_train[i].dtypes=='object']
conts = [i for i in x_train if x_train[i].dtypes!='object' and          len(x_train[i].value_counts())!=2]
cats = [i for i in x_train if i in catdums         and len(x_train[i].value_counts())>2]
dums = [i for i in x_train if i not in conts and i not in cats]

# Deal with imputing
catimpute = SimpleImputer(strategy='most_frequent')
contimpute = SimpleImputer(strategy='mean')
catimpute.fit(x_train[catdums])
contimpute.fit(x_train[conts])

# Impute based on x_train
x_train[catdums] = catimpute.transform(x_train[catdums])
x_train[conts] = contimpute.transform(x_train[conts])
x_val[catdums] = catimpute.transform(x_val[catdums])
x_val[conts] = contimpute.transform(x_val[conts])
x_test[catdums] = catimpute.transform(x_test[catdums])
x_test[conts] = contimpute.transform(x_test[conts])


# Make onehot and standardized
std = StandardScaler().fit(x_train[conts])
onehot = OneHotEncoder(categories='auto').fit(x_train[cats])


# In[67]:


pd.DataFrame(y_train).to_csv('y_train.csv')
pd.DataFrame(y_val).to_csv('y_val.csv')
pd.DataFrame(y_test).to_csv('y_test.csv')


# In[54]:


# Make prep function (transforms fit on x_train)
def xprep(X,
          cats=cats,dums=dums,conts=conts,
          std=std,onehot=onehot):
    return pd.concat([X[dums],
                      pd.DataFrame(std.transform(X[conts]),
                                   columns=conts,
                                   index=X.index),
                      pd.DataFrame(onehot.transform(X[cats]).toarray(),
                                   columns=get_names(cats,onehot.categories_),
                                   index=X.index)],axis=1)


# In[55]:


# Update x_train/val for 
x_train = xprep(x_train)
x_val = xprep(x_val)
x_test = xprep(x_test)


# In[56]:


# Save train/val/test indices and dfs for R MLM comparison
pd.DataFrame({'train':x_train.index}).to_csv('train_indices.csv')
pd.DataFrame({'val':x_val.index}).to_csv('val_indices.csv')
pd.DataFrame({'test':x_test.index}).to_csv('test_indices.csv')

x_train.to_csv('x_train.csv')
x_val.to_csv('x_val.csv')
x_test.to_csv('x_test.csv')

# Drop _STATE (only required for MLM)
x_train.drop('_STATE',axis=1,inplace=True)
x_val.drop('_STATE',axis=1,inplace=True)
x_test.drop('_STATE',axis=1,inplace=True)

# Save list of cat/ord/dum/cont variables
pd.DataFrame({'cats':cats}).to_csv('cats.csv', index=False)
pd.DataFrame({'catdums':catdums}).to_csv('catdums.csv', index=False)
pd.DataFrame({'conts':conts}).to_csv('conts.csv', index=False)
pd.DataFrame({'dums':dums}).to_csv('dums.csv', index=False)


# In[57]:


# pickle train/val/test x,y - make future testing faster
pickle.dump(x_train, open('x_train.pickle', 'wb'))
pickle.dump(x_val, open('x_val.pickle', 'wb'))
pickle.dump(x_test, open('x_test.pickle', 'wb'))
pickle.dump(y_train, open('y_train.pickle', 'wb'))
pickle.dump(y_val, open('y_val.pickle', 'wb'))
pickle.dump(y_test, open('y_test.pickle', 'wb'))

