
# Utility functions
from sklearn.preprocessing import MinMaxScaler

class Util:
    
    def __init__(self):
        self.name = "Util"

    def sort_dict_by_value(self,d):
        return dict(sorted(d.items(), key=lambda x:x[1], reverse=True))

    def filter_dict_by_value(self,ngrams,min_val=3):
        filtered_ngrams = {}
        for k,v in ngrams.items():
            if v >=min_val:
                filtered_ngrams[k] = v
        return filtered_ngrams

    # Function to write dictionaries to both json and csv
    def writeDictJsonCSV(self,dictionary,path_file):
        with open(f"{path_file}.json",'w') as fp:
            fp.write(json.dumps(dictionary))

        ngram_df = pd.DataFrame.from_dict(dictionary,orient='index')   
        ngram_df.to_csv(f"{path_file}.csv")

    # Input a series and output a list of lists with each maxn elements
    def series_to_chunked_list(self,series,maxn=25):
        l = list(series)
        return self.__chunk_list(l,maxn)
    
    # Chunk a list into a list of lists with maxn elements
    def __chunk_list(self,l,maxn=25):
        return [l[i:i + maxn] for i in range(0, len(l), maxn)]

    # Count named entities
    def count_entities(self,entities):
        counts = []
        for k,v in entities.items():
            counts.append((k,len(v))) 
        return sorted(counts, key=lambda x: x[1], reverse=True)
    
        # Function for calculating proportions of features
    def ratios(self,elements):
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
    def count_labels(self,string_labels):
        counts = dict()
        for rt in string_labels:
            counts[rt[1]] = counts.setdefault(rt[1],0) + 1
        return sorted(counts.items(), key=lambda x: x[1], reverse=True)
    
    def count_keys(self,key_count_dict):
        counts = dict()
        for k,v in key_count_dict.items():
            counts[k] = counts.setdefault(k,0) + v 
        return sorted(counts.items(), key=lambda x: x[1], reverse=True)
        
     # Total the values in list of tuples
    def tuple_values_total(self,tuples):
        tvs = [t[1] for t in tuples]
        return sum(tvs)

#### SCALING AND NORMALISING

    # Outliers

    def outlier_fence(self,series):
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
    def scale_min_max(self,df_cols):
        scaler = MinMaxScaler()
        return scaler.fit_transform(df_cols)

    # Normalise domain term counts
    def normalise_domain_counts(self,domain_counts,text_size):
        norms = {}
        for k,v in domain_counts.items():
            norms[k] = round(v*text_size,3)
        return norms

    def normalise_scaled(self,df,feature,norm_feature = 'text_scaled'):
        tempdf = df[[feature,norm_feature]].copy()
        tempdf['norm_scaled'] = tempdf.apply(lambda r: round(r[feature]/(r[norm_feature]+0.01),4),axis=1)
        return tempdf['norm_scaled']

    