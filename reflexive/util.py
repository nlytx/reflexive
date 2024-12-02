import os

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

from sklearn.preprocessing import MinMaxScaler

# File functions
def get_data_path_name(config,name,ext):
        return f"{config.local_path}{config.prefix}{name}{config.postfix}.{ext}"
        
def set_sub_dir(config,sub_dir=None):
    # check dir sub_dir exists
    if sub_dir:
        local_dir = f"{config.local_path}{sub_dir}/"
        logger.debug(f"local_dir: {local_dir}")
        dirExists = os.path.exists(local_dir)
        if not dirExists:
            logger.info(f"Creating subdirectory: {local_dir}")
            os.makedirs(local_dir)
    else:
        local_dir = local_path
    return local_dir
        


# Function to write dictionaries to both json and csv
def writeDictJsonCSV(dictionary,path_file):
    with open(f"{path_file}.json",'w') as fp:
        fp.write(json.dumps(dictionary))

    ngram_df = pd.DataFrame.from_dict(dictionary,orient='index')   
    ngram_df.to_csv(f"{path_file}.csv")
    
# Data functions
def sort_dict_by_value(d):
    return dict(sorted(d.items(), key=lambda x:x[1], reverse=True))

def filter_dict_by_value(ngrams,min_val=3):
    filtered_ngrams = {}
    for k,v in ngrams.items():
        if v >=min_val:
            filtered_ngrams[k] = v
    return filtered_ngrams

# Input a series and output a list of lists with each maxn elements
def series_to_chunked_list(series,maxn=25):
    l = list(series)
    return __chunk_list(l,maxn)

# Chunk a list into a list of lists with maxn elements
def __chunk_list(l,maxn=25):
    return [l[i:i + maxn] for i in range(0, len(l), maxn)]

# Count named entities
def count_entities(entities):
    counts = []
    for k,v in entities.items():
        counts.append((k,len(v))) 
    return sorted(counts, key=lambda x: x[1], reverse=True)

# Function for calculating proportions of features
def ratios(elements):
    etotal = sum([v[1] for v in elements])
    if etotal==0:
        return elements
    else:
        proportioned = []
        for element in elements:
            prop_val = round((element[1]/etotal),4)
            proportioned.append((element[0],prop_val))
        return proportioned



# Count labels associated with strings
def count_labels(string_labels):
    counts = dict()
    for rt in string_labels:
        counts[rt[1]] = counts.setdefault(rt[1],0) + 1
    return sorted(counts.items(), key=lambda x: x[1], reverse=True)

def count_keys(key_count_dict):
    counts = dict()
    for k,v in key_count_dict.items():
        counts[k] = counts.setdefault(k,0) + v 
    return sorted(counts.items(), key=lambda x: x[1], reverse=True)
    
# Total the values in list of tuples
def tuple_values_total(tuples):
    tvs = [t[1] for t in tuples]
    return sum(tvs)

#### SCALING AND NORMALISING

# Outliers

def outlier_fence(series):
    bounds = {}
    stats = series.describe()
    iqr = stats['75%'] - stats['25%']
    bounds["IQR"]=iqr
    upper = stats['75%']+1.5*iqr
    bounds["UPPER"]=upper
    lower = stats['25%']-1.5*iqr
    bounds["LOWER"]=lower
    return bounds

# MinMax Scaling
def scale_min_max(df_cols):
    scaler = MinMaxScaler()
    return scaler.fit_transform(df_cols)

# Normalise domain term counts
def normalise_domain_counts(domain_counts,text_size):
    norms = {}
    for k,v in domain_counts.items():
        norms[k] = round(v*text_size,3)
    return norms

def normalise_scaled(df,feature,norm_feature = 'text_scaled'):
    tempdf = df[[feature,norm_feature]].copy()
    tempdf['norm_scaled'] = tempdf.apply(lambda r: round(r[feature]/(r[norm_feature]+0.01),4),axis=1)
    return tempdf['norm_scaled']