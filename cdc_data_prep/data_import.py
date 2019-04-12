import numpy as np
import pandas as pd
import pickle
from sklearn.preprocessing import LabelBinarizer
import textract
from tabula import read_pdf


# Only do once, then pickle for faster import
# cdcdf_full = pd.read_sas('/Users/alex/Documents/ML/cdc/data/LLCP2017.XPT',encoding='utf-8')

# Fix import rounding errors (e.g. 0.7e-80 instead of 0)
# cdcdf_full = cdcdf_full.round(5)

# pickle.dump(cdcdf_full, open('cdcdf_full.pickle', 'wb'))

# Import from saved pickle.dump
cdcdf_full = pickle.load( open( "cdcdf_full.pickle", "rb" ) )

# Get Variable Summary (varnames and question for each)
text = textract.process("information/codebook17_llcp-v2-508.pdf",
                       encoding='utf-8')
text = text.splitlines()
text = [i.decode('utf-8') for i in text]
v_and_q = pd.DataFrame({
    'Variable': [i.split(':')[1].strip() for i in text if 'SAS Variable Name' in i],
    'Question': [i.split(':')[1].strip() for i in text if 'Question:' in i]
})
v_and_q.drop_duplicates(inplace=True)
v_and_q.reset_index(drop=True,inplace=True)

# Make label dictionaries

# alltables = read_pdf('information/codebook17_llcp-v2-508.pdf',multiple_tables=True,
#                   pages='2-195')
# pickle.dump(alltables, open('alltables.pickle', 'wb'))

alltables = pickle.load( open( "alltables.pickle", "rb" ) )
alltables = [i.loc[~i[0].isna(),:].reset_index(drop=True) for i in alltables]

filtered_tables = []
for table in alltables:
    filt = []
    ind = False
    for i in range(len(table[0])):
        filt.append(ind)
        if 'Type of Variable:' in table[0][i]:
            ind = True
        if 'SAS Variable Name:' in table[0][i]:
            ind = False
        if 'Value Value Label' in table[0][i]:
            ind = True
        if 'BLANK' in table[0][i]:
            ind = False
        if 'HIDDEN' in table[0][i]:
            ind = False
    filtered_tables.append(table.loc[filt,0].reset_index(drop=True))
    
def ex_value_dicts(exlist):
    # Remove floats, add ' None' to keys with no values
    exlist = [i + ' None' if len(i.split())==1 else i for i in exlist]
    outlist = [[i.split(':')[1].strip(), np.nan] \
                   if 'SAS Variable Name:' in i \
               else [' '.join(i.split(' ')[0:3]),
                    ' '.join(i.split(' ')[3:])] \
                   if i.split(' ')[0].isdigit() and i.split(' ')[1]=='-'
               else [i.split(' ')[0],
                    ' '.join(i.split(' ')[1:])] for i in exlist
    ]
    
    outlist = [[i[0],i[1][:25]] \
               if type(i[1]) is str else i \
               for i in outlist]

    varname = outlist[0][0].split(' ')[0]
    outdict = {d[0]: d[1] for d in outlist[1:]}
    
    # Drop stray invalid keys (whack a mole)
    outdict = {d[0]: d[1] for d in \
               [[i, outdict[i]] \
                for i in outdict \
                if i[0].isdigit() and ',' not in i and \
                'HIDDEN' not in i and 'BLANK' not in i]}
    
    outdict = dict(zip([float(i) if i[0].isdigit() and '-' not in i \
                        and ')' not in i
                        else i for i in outdict.keys()],
                       outdict.values()))
    return varname, outdict

dict_list = []
for table in filtered_tables:
    dict_list.append(ex_value_dicts(table))

    
value_dict = {}
for i in range(len(dict_list)-1):
    if dict_list[i][0] == dict_list[i+1][0]:
        value_dict[dict_list[i][0]] = {**dict_list[i][1],
                                       **dict_list[i+1][1]}
    if i > 0 and dict_list[i][0] != dict_list[i-1][0]:
        value_dict[dict_list[i][0]] = dict_list[i][1]

# Add the last dict
value_dict[dict_list[len(dict_list)-1][0]] = dict_list[len(dict_list)-1][1]

# Make dont know/refused/missing = np.nan and convert 88/888 to 0 dictionaries
miss_dicts = {}
for var in value_dict:
    miss_dicts[var] = {**{k: np.nan for k in value_dict[var].keys() \
                       if 'refused' in value_dict[var][k].lower() \
                       or "don’t know" in value_dict[var][k].lower() \
                       or "don't know" in value_dict[var][k].lower() \
                       or "missing" in value_dict[var][k].lower()},
                      **{k: 0 for k in value_dict[var].keys() \
                       if k==88.0 or k==888.0}}

# Drop variables that reference sequence or phone or weight
dropvars = [v_and_q['Variable'][i] \
                   for i in range(len(v_and_q['Variable'])) if \
                   'phone' in v_and_q['Question'][i].lower() \
                   or 'sequence' in v_and_q['Question'][i].lower() \
                   or 'weight' in v_and_q['Question'][i].lower()]


# Drop unnecessary/redundant vars
dropvars.extend(['_STSTR', '_STRWT', '_RAWRAKE', '_WT2RAKE', '_LLCPWT',  
'_RFHLTH', '_PHYS14D', '_MENT14D', '_IMPRACE', '_PRACE1',
'_MRACE1', '_HISPANC', '_RACE', '_RACEG21', 
'_AGEG5YR', '_AGE65YR', '_AGE_G', '_RFSMOK3',
'_CURECIG', '_MISFRT1', '_MISVEG1', '_FRT16A', '_VEG23A',
'_FRUITE1', '_VEGETE1', '_PACAT1', '_PA30021', '_PASTAE1',
'_RFSEAT2', '_PSU']) 

# Assign drop to analytic df
andf = cdcdf_full.drop(dropvars,axis=1)

# Keep specified relevant vars and computed vars (other vars are not
# formatted correctly)
keepvars = [i for i in andf.columns \
                 if i in ['_STATE', 'PHYSHLTH', 'MENTHLTH', 'SEX', 'MARITAL'] \
                 or i[0] is '_']
andf = andf[keepvars].copy()

# Make dont know/refused/missing = np.nan and convert 88/888 to 0 
for var in andf:
    andf[var] = [miss_dicts[var][i] if i in miss_dicts[var].keys()\
                     else i for i in andf[var]]

# Drop columns with more than 20% missing
andf.drop(andf.columns[andf.apply(lambda x: sum(x.isna())/len(x),axis=0)>.2],
          axis=1,inplace=True)
                      

# ID categorical
cats = []
for var in andf:
    if sum([type(i) is str for i in value_dict[var].keys()])==0:
        cats.append(var)
andf[cats] = andf[cats].astype('object')

# Convert v_and_q to dict
v_and_q_dict = dict(zip(v_and_q['Variable'],
                   v_and_q['Question']))

# Get state_ranks
state_ranks = pickle.load( open( "state_ranks.pickle", "rb" ) )

# Add state_label variable
andf['state_label'] = [value_dict['_STATE'][label] \
                       for label in andf['_STATE']]


# Take a look at the dicts
[i for i in state_ranks.keys()]

# Add gdp_pc, income_ineq, pop_dens_km, partisan_lean, and census_region to df
toadd = ['gdp_pc', 'income_ineq', 'pop_dens_km', 
         'partisan_lean', 'census_region']

for key in toadd:
    andf[key] = [state_ranks[key][obs] \
                 if obs in state_ranks[key].keys() \
                 else None for obs in andf['state_label']]


# Drop _STATE and state_label vars
andf.drop(['_STATE', 'state_label'], axis=1, inplace=True)


# ID all object vars with > 2 categories
# cat_cand = [i for i in andf if andf[i].dtypes=='O' \
#             and len(andf[i].value_counts())>2]
# print(cat_cand)
# # Manually inspect these varaibles and ID ordinal vs. cats
# ordinal_vars = []
# for var in cat_cand:
#     print(value_dict[var])
#     iscand = input(var+' ? ')
#     if iscand=='y':
#         ordinal_vars.append(var)
# print(ordinal_vars)
ordinal_vars = ['_ASTHMS1', '_LMTACT1', '_LMTWRK1', '_LMTSCL1', '_BMI5CAT', 
                '_CHLDCNT', '_EDUCAG', '_INCOMG', '_SMOKER3', '_ECIGSTS', 
                '_PA150R2', '_PA300R2']

# Change ordinal object vars to float
andf[ordinal_vars] = andf[ordinal_vars].astype('float')

# Convert 2-cardinal cats to binary dummies
twocats = [var for var in andf if len(andf[var].value_counts())==2 \
           and var in value_dict]
renames = dict(zip(twocats,
               [i+'_'+value_dict[i][2][:6] for i in twocats]))
andf = andf.rename(index=str,columns=renames)

dums = [i for i in renames.values()]

andf[dums] = andf[dums]-1

# Convert to float
andf[dums] = andf[dums].astype('float')

# Get dummies for census_region
lb = LabelBinarizer()

lb.fit(andf['census_region'].astype(str))

andf = pd.concat([andf.reset_index(drop=True),
                  pd.DataFrame(lb.transform(andf['census_region'].astype(str)),
                               columns=['Region_'+ i for i in lb.classes_])],
                 axis=1)

andf.drop(['census_region'],axis=1,inplace=True)

# Make ints floats
intvars = [i for i in andf.columns if andf[i].dtypes=='int']

andf[intvars] = andf[intvars].astype('float')


data_description = '''The dataframe andf (analytic dataframe) does not include variables that 
references sequences, phone type, or weights. It also drops other variables
that I considered unnecessary or redundent:

'_STSTR', '_STRWT', '_RAWRAKE', '_WT2RAKE', '_LLCPWT',  
'_RFHLTH', '_PHYS14D', '_MENT14D', '_IMPRACE', '_PRACE1',
'_MRACE1', '_HISPANC', '_RACE', '_RACEG21', 
'_AGEG5YR', '_AGE65YR', '_AGE_G', '_RFSMOK3',
'_CURECIG', '_MISFRT1', '_MISVEG1', '_FRT16A', '_VEG23A',
'_FRUITE1', '_VEGETE1', '_PACAT1', '_PA30021', '_PASTAE1',
'_RFSEAT2', '_PSU'

andf does not include intermediate variables (those ending with _).

Any values with dont know, refused, or missing were recoded as nan.

Variables with >20% missing were dropped.

Variables deemed to be continous were kept as floats, all others were
coded as objects.

The _STATE variable was converted to other numerical state-level indicators
(see state_label), then dropped. Those state_label vars were convereted to dummies.

Categorical variables with only 2 levels were renamed and recoded as simple binary 
dummies.

'''

# Make data_import dictionary

data_import = {'andf':andf, 'cdcdf_full':cdcdf_full, 'data_description':data_description,
'value_dict':value_dict, 'v_and_q_dict':v_and_q_dict}

pickle.dump(data_import, open('data_import.pickle', 'wb'))

