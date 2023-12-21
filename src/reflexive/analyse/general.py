
import logging,coloredlogs
import pandas as pd
import json

from reflexive.common.parameters import Parameters
from reflexive.common.util import Util

coloredlogs.install(level='INFO')

class General:
    
    logger = logging.getLogger(__name__)
    
    def __init__(self,parameters:Parameters):
        #print(parameters)
        self.__parameters = parameters.all_parameters()
        self.logger.debug(f"Parameters: {self.__parameters}")


    def general_analytics(self,df):
        util = Util()
        custom_df = df.copy() 
        custom_df["text_length"] = df.text.apply(lambda x: len(x))
        if (len(custom_df)>1):
            custom_df["text_scaled"] = util.scale_min_max(custom_df[['text_length']])
        else:
            custom_df["text_scaled"] = 1
        return custom_df


    def remove_IQR_outliers(self,df):
        tempdf = df.copy()
        # Calculate text length
        tempdf["text_length"] = tempdf.text.apply(lambda t: len(t))
        fence = Util.outlier_fence(tempdf.text_length)  
        print(fence)
        # Check change with removed outliers
        checkdf = tempdf[tempdf.text_length<fence['UPPER']]
        checkdf.reset_index(drop=True,inplace=True)
        print("Original:",len(tempdf))
        print(tempdf.describe())
        print()
        print("Outliers:",len(tempdf)-len(checkdf))
        print()
        print("No outliers:",len(checkdf))
        print(checkdf.describe())
        return checkdf

    # Parse text for domain terms
    def parse_domain_terms(self,text,domain_terms):
        matched_terms = {}
        for dtk,dtv in domain_terms.items():
            matched_terms[dtk] = []
            for term in dtv:
                if term[0]=='_': #acronym - treat as whole word
                    regex = r"\b{}\b".format(term[1:])
                    matches = re.findall(regex,str.lower(text))
                    if len(matches)>0:
                        matched_terms[dtk].append((term[1:],len(matches)))
                else:
                    count = str.lower(text).count(term)
                    if count > 0:
                        matched_terms[dtk].append((term,count))
        return matched_terms
    
    
    def get_top_ngrams(self,text_series,min_val=3):
        ngrams = {}
        for text in text_series:
            self.__ngrams345(text,ngrams)
        #print("Generated 3,4,5 ngrams:", len(ngrams))
        f_ngrams = self.filter_dict_by_value(ngrams,min_val)
        return self.sort_dict_by_value(f_ngrams)

    def get_top_ngrams_for_text(self,text,top_ngrams):
        ngrams = self.__ngrams345(text,{})
        return {key: ngrams[key] for key in top_ngrams.keys() if key in ngrams}

    def ngram_counts(self,ref_top_ngrams):
        return sum(ref_top_ngrams.values())
    
        # Given text and number of terms, create ngrams from the text
    def __make_ngrams(self,text, n=1):
        # Replace all none alphanumeric characters with spaces
        s = re.sub(r'[^a-zA-Z0-9\s]', ' ', text.lower())
        
        tokens = [token for token in s.split(" ") if token != ""]
        ngrams = zip(*[tokens[i:] for i in range(n)])
        return [" ".join(ngram) for ngram in ngrams]

    # Generate 3,4,5 -grams
    def __ngrams345(self,text,ngrams):
        ngrams3 = self.__make_ngrams(text,3)
        for n in ngrams3:
            ngrams[n] = ngrams.get(n,0)+1
        ngrams4 = self.__make_ngrams(text,4)
        for n in ngrams4:
            ngrams[n] = ngrams.get(n,0)+1
        ngrams5 = self.__make_ngrams(text,5)
        for n in ngrams5:
            ngrams[n] = ngrams.get(n,0)+1
        return ngrams
    

    # Count domain terms
    def count_domain_terms(self,terms):
        counts = {}
        for k,v in terms.items():
            for term in v:
                counts[k] = counts.setdefault(k,0) + term[1]
        return counts


    # Ratio between action POS and object POS
    def action_object_ratio(self,pos_ratios,action_pos = ['VERB'],object_pos = ['NOUN','PROPN']):
        ap = [s[1] for s in pos_ratios if s[0] in action_pos]
        if ap:
            aps = sum(ap)
        else:
            aps = 0
        op = [s[1] for s in pos_ratios if s[0] in object_pos]
        if op:
            ops = sum(op)
        else:
            ops = 1 #avoid divide zero error - only happens with aps of 1
            #print("aps",aps,"ops",ops)
        return aps/ops