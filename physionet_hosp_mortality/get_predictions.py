import pickle
import pandas as pd
import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.preprocessing import OneHotEncoder
from sklearn.impute import SimpleImputer

q99_dict = pickle.load(open('q99_dict.pickle', 'rb'))

drop_vars = ['Cholesterol', 'RespRate', 
                 'TroponinI', 'TroponinT', 
                 'MechVent']
    
static_vars = ['RecordID', 'Age', 'Gender', 
               'Height', 'ICUType']
    
keep_vars = ['GCS', 'HR', 'NIDiasABP', 'NIMAP', 'NISysABP', 'Temp',
             'Urine', 'HCT', 'BUN', 'Creatinine', 'Glucose', 'HCO3',
             'Mg', 'Platelets', 'K', 'Na', 'WBC', 'pH', 'PaCO2', 'PaO2',
             'DiasABP', 'FiO2', 'MAP', 'SysABP', 'SaO2', 'Albumin',
             'ALP', 'ALT', 'AST', 'Bilirubin', 'Lactate', 'Weight']

seq_vars = ['HR', 'Temp', 'Urine']
day_vars = ['BUN', 'Creatinine', 'Glucose', 'HCO3', 'HCT', 'K', 'Mg', 'Na',
            'Platelets', 'WBC']
stay_dense = ['DiasABP', 'GCS', 'MAP', 'NIDiasABP', 'NIMAP', 'NISysABP', 
              'PaCO2', 'PaO2', 'SysABP', 'Weight', 'pH']
stay_sparse = ['ALP', 'ALT', 'AST', 'Albumin', 'Bilirubin', 'FiO2', 
               'Lactate', 'SaO2', 'pao2_fio2_r']

stay_sparse_dict = {
    'ALP': [44, 147],
    'ALT': [7, 56],
    'AST': [10, 40],
    'Albumin': [3.4, 5.4],
    'Bilirubin': [0.1, 1.2],
    'FiO2': [-np.inf, np.inf],
    'Lactate': [-np.inf, 2],
    'SaO2': [93, 97],
    'pao2_fio2_r': [202, np.inf]
}

# Functions
def get_time(X, time_vars, agg_method=min):
    '''Returns long df from raw df'''
    time_df = X.loc[np.array([True if i in time_vars else False \
                              for i in X.Parameter])]
    pivot_df = time_df.set_index(['PATIENT_ID', 'Time'], 
                                 append=True).pivot(columns='Parameter')
    groupby_df = pivot_df.groupby(['PATIENT_ID', 'Time']).agg(agg_method)
    groupby_df.columns = groupby_df.columns.get_level_values(1)
    return groupby_df.reset_index()

# Extract static variables:
def get_static(X, static_vars):
    '''Parameters:
    X: Computing in Cardiology Challenge DataFrame
    Returns: Static variables ['PATIENT_ID' 'RecordID' 'Age' 'Gender' 'Height' 
    'ICUType' 'Weight'] in wide format (i.e. PATIENT_ID is row index)'''
    
    keep_obs = np.array([True if i in static_vars else False \
                           for i in X.Parameter])
    outdf = X.loc[keep_obs & np.array(X.Time=='00:00'),
                  ['PATIENT_ID', 'Parameter', 'Value']]
    return outdf.pivot(index='PATIENT_ID', columns='Parameter', values='Value')

def assign_interval(l, interval, unit, return_int_len=False,
                   return_all_bins=False):
    '''Returns ceiling value of interval (closed right).
    If value==0, assigned to lowest interval
    
    l: list to get interval bin assignments for
    interval: bin width
    unit: time, 'hour', or 'minute'
    return_int_len: return total length of all bins?
    '''
    if unit=='hour':
        max_time = int(48/interval)
    elif unit=='minute':
        max_time = int(48*60/interval)
    else:
        return 'bad unit specification'
    
    int_floors = [i*interval for i in range(0,max_time)]
    int_ceilings = [i*interval for i in range(1,max_time+1)]
    
    out_l = []
    for obs in l:
        get_interval=True
        for i in range(len(int_ceilings)):
            if get_interval & (obs==0):
                out_l.append(interval)
                get_interval=False
            if get_interval & (int_floors[i] < obs <= int_ceilings[i]):
                out_l.append(int_ceilings[i])
                get_interval=False   
    if return_int_len:
        return out_l, len(int_ceilings)
    if return_all_bins:
        return out_l, int_ceilings
    else:
        return out_l

def summary_extract(x):
    '''use with lambda to get summary stats'''
    x_min = x.min()
    x_max = x.max()
    x_med = x.median()
    nan_strip = [i for i in x if str(i) != 'nan']
    if len(nan_strip) > 0:
        x_first = nan_strip[0]
    else:
        x_first = np.nan
    if len(nan_strip) > 0:
        x_last = nan_strip[len(nan_strip)-1]
    else:
        x_last = np.nan
    x_n = len(nan_strip)
    return [x_min, x_max, x_med, x_first, x_last, x_n]

def stay_dense_extract(df, varlist):
    '''for getting summary stats for entire stay vars'''
    extract_df = df.groupby('PATIENT_ID')[varlist].agg(
        lambda x: summary_extract(x))
    outdf = pd.DataFrame()
    for var in extract_df.columns:
        colnames = [var+'_'+i for i in ['min', 'max', 'med', 
                                        'first', 'last', 'n']]
        
        loop_df = pd.DataFrame([np.array(i) for i in extract_df[var]],
                                columns=colnames)
        outdf = pd.concat([outdf, loop_df], axis=1)
    return outdf

def day_var_extract(df, varlist):
    '''returns summary stats for each 24 hour period of stay'''
    # Deal with patients with no obs after 24hrs
    bad_mask = df.groupby('PATIENT_ID')['Hours'].max()<=24
    bad_ids = bad_mask[bad_mask].index
    filler_df = pd.DataFrame({
        'PATIENT_ID': bad_ids,
        'Hours': [47.9 for i in range(len(bad_ids))]
                             })
    df = pd.merge(df, filler_df, on=['PATIENT_ID', 'Hours'], how='outer')
    df.sort_values(by=['PATIENT_ID', 'Hours'], inplace=True)
    
    gb_time = assign_interval(df['Hours'], 24, 'hour')
    extract_df = df.groupby(['PATIENT_ID', gb_time])[varlist].agg(
        lambda x: summary_extract(x))
    outdf = pd.DataFrame()
    for var in extract_df.columns:
        colnames = [var+'_'+i for i in ['min_24', 'max_24', 'med_24', 
                                        'first_24', 'last_24', 'n_24',
                                       'min_48', 'max_48', 'med_48', 
                                        'first_48', 'last_48', 'n_48']]
        
        loop_df = pd.DataFrame(
            np.array([np.array(i) for i in extract_df[var]]).reshape(-1,12),
            columns=colnames
        )
        outdf = pd.concat([outdf, loop_df], axis=1)
    return outdf  
    
def extract_trends(df, varlist, time_var='Hours'):
    '''returns linear trend across entire stay for specified vars.
    this takes some time.'''
    outlist = []
    for var in varlist:
        pat_vector = []
        for patient in df.PATIENT_ID.unique():
            x = df.loc[df.PATIENT_ID==patient,[time_var, var]].dropna()
            A = np.vstack([x[time_var], np.ones(len(x))]).T
            y = x[var].to_numpy()
            m, c = np.linalg.lstsq(A, y, rcond=None)[0]
            if len(y)>1: 
                pat_vector.append(m)
            else:
                pat_vector.append(np.nan)
        outlist.append(np.array(pat_vector))
    return pd.DataFrame(np.array(outlist).T,
                       columns=[i+'_trend' for i in varlist])

def abnormal_cats(x, bounds):
    '''Returns 0 for missing, 1 for within normal, 2 for abnormal based
    on supplied bounds

    x
        value
    bounds
        list of length 2 specifying bounds: [lower, upper]'''
    if np.isnan(np.sum(x)):
        return 0
    elif bounds[0] <= x <= bounds[1]:
        return 1
    else:
        return 2

def stay_sparse_extract(df, varlist, cutoff_dict):
    '''extract categorical features from sparse variables.
    0=nan, 1=normal, 2=abnormal'''
    new_features = []
    for var in varlist:
        loop_list = [abnormal_cats(i,stay_sparse_dict[var]) for i in df[var]]
        loop_features = pd.Series(loop_list).groupby(df.PATIENT_ID).max()
        new_features.append(np.array(loop_features))
    features_df = pd.DataFrame(np.array(new_features).T, 
                               columns=[i+'_cats' for i in varlist])
    return features_df

def collapse_time(df, varlist, interval):
    '''returns time_df as df with specified intervals for all ids'''
    # Get intervals, bins
    intervals, bins = assign_interval(df['Hours'], 4, 'hour',
                                     return_all_bins=True)
    # Start seq df
    p_id = df['PATIENT_ID'].unique()
    seq_label = 'Time_' + str(interval) + '_hours'
    seq_df = pd.DataFrame({
        'PATIENT_ID': [i for j in \
                       [[i]*len(bins) for i in p_id] \
                      for i in j],
        seq_label: [i for j in \
                    [bins for i in p_id] \
                   for i in j]
    })
    
    # Add intervals to df
    df[seq_label] = intervals
    
    # Mean Bins
    mean_bins = df.groupby(['PATIENT_ID', 
                            seq_label])[varlist].mean().reset_index()
    new_column_names = [i for i in mean_bins.columns]
    new_column_names[-3:] = [i + '_mean' for i in new_column_names[-3:]]
    mean_bins.columns = new_column_names
    
    # N/Samples Bins
    ns_bins = df.groupby(
        ['PATIENT_ID', seq_label]
    )[varlist].agg(lambda x: sum(x.isna()==False)).reset_index()
    new_column_names = [i for i in ns_bins.columns]
    new_column_names[-3:] = [i + '_ns' for i in new_column_names[-3:]]
    ns_bins.columns = new_column_names
    
    # Finish seq_df
    seq_df = pd.merge(seq_df, 
                      mean_bins, 
                      on=['PATIENT_ID', seq_label], 
                      how='outer')
    
    seq_df = pd.merge(seq_df, 
                      ns_bins, 
                      on=['PATIENT_ID', seq_label], 
                      how='outer')
    
    # Make np.nan 0:
    seq_df.iloc[:,-3:] = seq_df.iloc[:,-3:].replace(np.nan, 0)
    
    # Replace missing bins with patient-level mean
    imputed = seq_df.groupby('PATIENT_ID')[mean_bins.columns[2:]].transform(
        lambda x: x.fillna(x.mean())
    )
    seq_df.loc[:,mean_bins.columns[2:]] = imputed
    
    return seq_df

def seq_impute(df, varlist, seq_dict):
    '''imputes empty sequences with specified means in seq_dict'''
    for var in varlist:
        for ids in df.loc[df[var].isna(),
                          ['PATIENT_ID', var]].PATIENT_ID.unique():
            df.loc[(df[var].isna()) & (df.PATIENT_ID==ids),
                   var] = np.array(seq_dict[var])
    return df

# Load mean_seq
mean_seq = pickle.load(open('mean_seq.pickle', 'rb'))

class MakeStatic(BaseEstimator, TransformerMixin):
    '''returns fully transformed df with all calculated vars. this
    takes some time.'''
    # Get dicts/lists
    def __init__(self, keep_vars=keep_vars, 
                 static_vars=static_vars, 
                 q99_dict=q99_dict,
                 seq_vars=seq_vars, 
                 day_vars=day_vars, 
                 stay_dense=stay_dense, 
                 stay_sparse=stay_sparse,
                 stay_sparse_dict=stay_sparse_dict):
        self.keep_vars = keep_vars
        self.static_vars = static_vars
        self.q99_dict = q99_dict
        self.seq_vars = seq_vars
        self.day_vars = day_vars
        self.stay_dense = stay_dense
        self.stay_sparse = stay_sparse
        self.stay_sparse_dict = stay_sparse_dict
    
    def fit(self, X, y=None):
        return self
    
    def transform(self, X, y=None):
        # Get time vars and replace -1 with nan
        self.X_time = get_time(X,
                               time_vars=self.keep_vars).replace(-1,np.nan)
        # Get static vars and replace -1 with nan
        self.X_static = get_static(X, 
                                   static_vars).replace(-1,np.nan)
        
        # Drop extreme values
        for var in self.keep_vars:
            self.X_time.loc[self.X_time[var] > self.q99_dict[var],
                            var] = np.nan
        self.X_static.loc[self.X_static['Height'] > self.q99_dict['Height'],
                         'Height'] = np.nan
        self.X_static.loc[self.X_static['Age'] > self.q99_dict['Age'],
                         'Age'] = np.nan
        # Impute Gender
        self.X_static['Gender'].fillna(1, inplace=True)
        # Add pao2_fio2_r and Hours to time
        self.X_time['pao2_fio2_r'] = self.X_time['PaO2']/self.X_time['FiO2']
        self.X_time['Hours'] = [float(i.split(':')[0]) + 
                                float(i.split(':')[1])/60 
                                for i in self.X_time.Time]
        # Drop RecordID
        self.X_static.drop('RecordID', axis=1, inplace=True)
        # Save PATIENT_ID order for reference
        self.PATIENT_IDs_ = self.X_static.index
        
        # Make static frames for day_var, stay_dense, stay_sparse, trends
        # and combine with static
        self.X_merge_ = pd.concat([
            self.X_static.reset_index(drop=True),
            day_var_extract(self.X_time, 
                            [i for j in [self.day_vars, 
                                         self.seq_vars] for i in j]),
            stay_dense_extract(self.X_time, self.stay_dense),
            stay_sparse_extract(self.X_time, 
                                self.stay_sparse, 
                                self.stay_sparse_dict),
            extract_trends(self.X_time, 
                           [i for j in 
                           [self.stay_dense, 
                            self.day_vars, 
                            self.seq_vars] 
                           for i in j])
        ], axis=1)

        return self.X_merge_
    
class MakeSeq(BaseEstimator, TransformerMixin):
    '''returns df with sequences'''
    def __init__(self, seq_vars, interval=4, mean_seq=mean_seq):
        self.seq_vars = seq_vars
        self.mean_seq = mean_seq
        self.interval = interval
    
    def fit(self, X, y=None):
        return self
    
    def transform(self, X, y=None):
        self.X_seq = get_time(X, self.seq_vars)
        self.X_seq['Hours'] = [float(i.split(':')[0]) + 
                                float(i.split(':')[1])/60 
                                for i in self.X_seq.Time]
        self.X_seq = collapse_time(self.X_seq,
                                   self.seq_vars, 
                                   self.interval)
#         Impute missing seqs with mean seq
        self.X_seq = seq_impute(self.X_seq,
                               [i+'_mean' for i in self.seq_vars],
                               self.mean_seq)
        return self.X_seq

class OneHotImpute(BaseEstimator, TransformerMixin):
    '''performs one-hot encoding for categoricals and then imputes median
    for other vars'''
    def __init__(self, one_hot_vars):
        self.one_hot_vars = one_hot_vars
        
    def fit(self, X, y=None):
        self.oh = OneHotEncoder(categories='auto',sparse=False)
        self.oh.fit(X.loc[:, self.one_hot_vars])
        self.med_impute_vars = [i for i in X.columns 
                                if i not in self.one_hot_vars]
        self.si = SimpleImputer(missing_values=np.nan,
                                strategy='median')
        self.si.fit(X.loc[:, self.med_impute_vars])
        return self
    
    def transform(self, X, y=None):
        self.X_ = pd.concat([
            pd.DataFrame(
                self.oh.transform(X.loc[:, self.one_hot_vars]),
                columns = self.oh.get_feature_names()
            ),
            pd.DataFrame(
                self.si.transform(X.loc[:, self.med_impute_vars]),
                columns = X.loc[:, self.med_impute_vars].columns
            )
        ], axis=1)
        return self.X_
    
raw_df = pd.read_csv('test_data.csv')

pipe = pickle.load(open('pipe_transform.pickle', 'rb'))
std_scale = pickle.load(open('standard_scaler.pickle', 'rb'))
xgb_drop = pickle.load(open('xgb_drop.pickle', 'rb'))
xgb_model = pickle.load(open('final_class.pickle', 'rb'))

pipe_df = pipe.transform(raw_df)

std_df = std_scale.transform(pipe_df)

std_df = pd.DataFrame(std_df, columns=pipe_df.columns)
drop_df = std_df.drop(xgb_drop, axis=1)

preds = xgb_model.predict(drop_df.to_numpy())

pred_df = pd.DataFrame({
    'PATIENT_ID': raw_df.PATIENT_ID.unique(),
    'Predictions': preds
})

pred_df.to_csv('test_predictions.csv', index=False)