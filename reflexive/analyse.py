
import json
import pandas as pd
import re

from reflexive import util
from reflexive import cfg
from reflexive import session
import reflexive as rfx

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class Nlp:
    aws:session.AWS = None
    config:cfg.Config = None
    
    top_ngrams = {}
    
    
    def __init__(self,aws):
        self.aws = aws
        self.aws = aws
        self.config = self.aws.config
        
    ### GENERAL ANALYSIS FUNCTIONS ######
    
    #checked
    def text_length(self,df,text_col_name='text'):
        self.config.text_col_name = text_col_name
        custom_df = df.copy() 
        custom_df["text_length"] = df[text_col_name].apply(lambda x: len(x))
        if (len(custom_df)>1):
            custom_df["text_scaled"] = util.scale_min_max(custom_df[['text_length']])
        else:
            custom_df["text_scaled"] = 1
        return custom_df

    #checked
    def remove_IQR_outliers(self,df):
        fence = util.outlier_fence(df.text_length)
        logger.debug("Fence: %s",repr(fence))
        if fence['LOWER']==fence['UPPER']:
            logger.info("No fence, returning original df")
            return df
        else:
            tempdf = df.copy()
            # Check change with removed outliers
            checkdf = tempdf[tempdf.text_length<fence['UPPER']]
            checkdf.reset_index(drop=True,inplace=True)
            logger.debug("Original:",len(tempdf))
            logger.debug(tempdf.describe())
            logger.info:("Outliers: %s",repr(len(tempdf)-len(checkdf)))
            logger.debug("No outliers:",len(checkdf))
            logger.debug(checkdf.describe())
            return checkdf
     
    #checked   
    #Add domain terms to config
    def add_domain_terms(self,domain_terms):
        self.config.domain_terms = domain_terms
    
    #checked    
    # Parse text for domain terms
    def parse_text_domain_terms(self,text):
        matched_terms = {}
        for dtk,dtv in self.config.domain_terms.items():
            temp_matches = []
            for term in dtv:
                if term[0]=='_': #acronym - treat as whole word
                    regex = r"\b{}\b".format(term[1:])
                    matches = re.findall(regex,str.lower(text))
                    if len(matches)>0:
                        temp_matches.append((term[1:],len(matches)))
                else:
                    count = str.lower(text).count(term)
                    if count > 0:
                        temp_matches.append((term,count))
            matched_terms[dtk] = dict(temp_matches)
        return dict(matched_terms)
    
    #checked
    def match_domain_terms(self,df):
        custom_df = df.copy() 
        custom_df["domain_terms"] = df[self.config.text_col_name].apply(lambda t: self.parse_text_domain_terms(t))
        custom_df["domain_counts"] = custom_df["domain_terms"].apply(lambda d: self.__count_domain_terms(d))
        return custom_df
    
    #checked
    # Count domain terms
    def __count_domain_terms(self,domain_terms):
        domain_counts = {}
        for domain,terms in domain_terms.items():
            domain_counts[domain] = sum(terms.values())
        return domain_counts
    
    #checked
    def get_top_ngrams(self,text_series,min_val=3):
        ngrams = {}
        for text in text_series:
            self.__ngrams345(text,ngrams)
        #print("Generated 3,4,5 ngrams:", len(ngrams))
        f_ngrams = util.filter_dict_by_value(ngrams,min_val)
        self.top_ngrams =  util.sort_dict_by_value(f_ngrams)
        return self.top_ngrams
        

    #checked
    def match_top_ngrams(self,df):
        custom_df = df.copy() 
        custom_df["top_ngrams"] = df[self.config.text_col_name].apply(lambda t: self.parse_text_top_ngrams(t))
        custom_df["top_ngrams_count"] = custom_df["top_ngrams"].apply(lambda n: self.__ngram_counts(n))
        return custom_df
    
    #checked
    def parse_text_top_ngrams(self,text):
        ngrams = self.__ngrams345(text,{})
        return {key: ngrams[key] for key in self.top_ngrams.keys() if key in ngrams}

    #checked
    def __ngram_counts(self,ref_top_ngrams):
        return sum(ref_top_ngrams.values())
    
    #checked
        # Given text and number of terms, create ngrams from the text
    def __make_ngrams(self,text, n=1):
        # Replace all none alphanumeric characters with spaces
        s = re.sub(r'[^a-zA-Z0-9\s]', ' ', text.lower())
        tokens = [token for token in s.split(" ") if token != ""]
        ngrams = zip(*[tokens[i:] for i in range(n)])
        return [" ".join(ngram) for ngram in ngrams]

    #checked
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
    

    #### COMPREHEND ANALYSIS

    #checked
    def comprehend_analysis(self,comprehend,df):
        self.analysis_types = self.config.analysis_types
        #print(type(df.text))
        # chunk the text for batch analysis
        chunked_text = util.series_to_chunked_list(series=df[self.config.text_col_name])
        print("Number of chunks:",len(chunked_text))
        # start batch analysis
        chunked_results = comprehend.get_multiple_batch_analysis(chunked_text)
        print("Finished Analysis.")
        # write to file
        print("Writing data to file...")
        with open(f"{self.config.local_path}{self.config.prefix}analysis_chunks{self.config.postfix}.json", "w") as fp:
            json.dump(chunked_results,fp)            
        print("DONE!")
        # unchunk
        final_results = {}
        for key in chunked_results.keys():
            final_results[key] = comprehend.unbatch_results(self.analysis_types[key],chunked_results[key])
            print("Finished Unbatching",key," -  Writing data to file...")
            filename = f"{self.config.local_path}{self.config.prefix}{key}{self.config.postfix}.json"
            with open(filename, "w") as fp:
                json.dump(final_results[key],fp)            
        print("DONE!")
        # Save final_results for reload if necessary
        with open(f"{self.config.local_path}{self.config.prefix}final_results{self.config.postfix}.json", "w") as fp:
            json.dump(final_results,fp) 
        return final_results

    #checked
    def check_results(self,results):
        print("Checking for errors...")
        for key in results.keys():
            errors = results[key]['errors']
            print(f"Errors for {key}: {errors}")
        print()
        print("Checking that we have results for all docs")
        for key in results.keys():
            num_results= len(results[key]['results'])
            print(f"Number of results for {key}: {num_results}")
        return errors

    #checked
    def add_results_to_df(self,results,df):
        for key in results.keys():
            rs = results[key]['results']
            newresults = {}
            for oldkey in rs.keys():
                newresults[int(oldkey)] = rs[oldkey] # Need to change keys to int to properly add to dataframe
            df[key] = pd.Series(newresults)
        return df

    #checked
    def comprehend_analytics(self,df):
        temp_df = df.copy()
        temp_df = self.keyphrase_analytics(temp_df)
        temp_df = self.named_entity_analytics(temp_df)
        temp_df = self.targeted_sentiment_analytics(temp_df)
        temp_df = self.syntax_analytics(temp_df)
        return temp_df
    
    #checked
    def keyphrase_analytics(self,df):
        df["key_phrases"] = df.KeyPhraseResults.apply(self.parse_keyPhraseResults)
        df["key_phrase_counts"] = df.key_phrases.apply(util.count_keys)
        df["key_phrases_total"] = df.key_phrase_counts.apply(util.tuple_values_total)
        if (len(df)>1):
            df["key_phrases_scaled"] = util.scale_min_max(df[['key_phrases_total']])
        else:
            df["key_phrases_scaled"] = 1
        # Normalise based on text_scaled
        df['key_phrases_norm'] = util.normalise_scaled(df,'key_phrases_scaled')
        return df

    #checked
    def named_entity_analytics(self,df):
        df["named_entities"] = df.TargetedSentimentResults.apply(self.parse_namedEntities)
        df['named_entity_counts'] = df.named_entities.apply(util.count_entities)
        df["named_entity_ratios"] = df.named_entity_counts.apply(util.ratios)
        df["named_entities_total"] = df.named_entity_counts.apply(util.tuple_values_total)
        if (len(df)>1):
            df["named_entities_scaled"] = util.scale_min_max(df[['named_entities_total']])
        else:
            df["named_entities_scaled"] = 1
        df['named_entities_norm'] = util.normalise_scaled(df,'named_entities_scaled')
        return df
    
    #checked
    def targeted_sentiment_analytics(self,df):
        df["targeted_sentiment"] = df.TargetedSentimentResults.apply(self.parse_targetedSentimentResults)
        df['targeted_sentiment_counts'] = df.targeted_sentiment.apply(util.count_entities)
        df["targeted_sentiment_ratios"] = df.targeted_sentiment_counts.apply(util.ratios)
        df["targeted_sentiment_total"] = df.targeted_sentiment_counts.apply(util.tuple_values_total)
        if (len(df)>1):
            df["targeted_sentiment_scaled"] = util.scale_min_max(df[['targeted_sentiment_total']])
        else:
            df["targeted_sentiment_scaled"] = 1
        df['targeted_sentiment_norm'] = util.normalise_scaled(df,'targeted_sentiment_scaled')
        return df
    
    #checked
    def syntax_analytics(self,df):
        df["pos_tags"] = df.SyntaxResults.apply(self.parse_syntaxResults)
        df['pos_tag_counts'] = df.pos_tags.apply(util.count_labels)
        df["pos_tag_ratios"] = df.pos_tag_counts.apply(util.ratios)
        df["pos_tags_total"] = df.pos_tag_counts.apply(util.tuple_values_total)
        if (len(df)>1):
            df["pos_tags_scaled"] = util.scale_min_max(df[['pos_tags_total']])
        else:
            df["pos_tags_scaled"] = 1
        df['pos_tags_norm'] = util.normalise_scaled(df,'pos_tags_scaled')
        return df    
    
    #checked
    # Parse key_phrases results - include all above threshold
    def parse_keyPhraseResults(self,keyPhraseResults,threshold=0.95,min_count=1):
        phrases = {}
        filtered = [str.lower(r['Text']) for r in keyPhraseResults if r['Score'] > threshold]
        for phrase in filtered:
            phrases[phrase] = phrases.get(phrase,0)+1

        filtered_phrases = {k:v for k,v in phrases.items() if v >= min_count}
        return util.sort_dict_by_value(filtered_phrases)

    #checked
    # Parse syntax results - include specific postags
    def parse_syntaxResults(self,syntax_results,postags_keep = ['ADV','VERB','AUX','ADJ','NOUN','PRON','PROPN']):
        sequence = list()
        for token in syntax_results:
            tag = token['PartOfSpeech']['Tag']
            if tag in postags_keep:
                sequence.append((str.lower(token['Text']),tag))
        return sequence

    #checked
    # Parse targeted sentiment results - keep non-neutral above threshold
    def parse_targetedSentimentResults(self,targetedSentiment_results,threshold = 0.4):
        sents = dict()
        for grp in targetedSentiment_results:
            for mention in grp["Mentions"]:
                if mention['Score'] >= threshold:
                    if not "NEUTRAL" in mention['MentionSentiment']['Sentiment']:
                        k = mention['MentionSentiment']['Sentiment']
                        text = str.lower(mention['Text'])
                        sents.setdefault(k,{text}).add(text)
        for k,v in sents.items():
            sents[k] = list(v) # change set to list
        return sents

    #checked
    # Parse targeted sentiment results for named entities
    def parse_namedEntities(self,targetedSentimentResults,threshold = 0.1):
        ents = dict()
        for grp in targetedSentimentResults:
            for mention in grp["Mentions"]:
                if mention['Score'] >= threshold:
                    k = mention['Type']
                    text = str.lower(mention['Text'])
                    ents.setdefault(k,{text}).add(text)
        for k,v in ents.items():
            ents[k] = list(v) # change set to list
        return ents       

    #--
    # Ratio between action POS and object POS
    # def action_object_ratio(self,pos_ratios,action_pos = ['VERB'],object_pos = ['NOUN','PROPN']):
    #     ap = [s[1] for s in pos_ratios if s[0] in action_pos]
    #     if ap:
    #         aps = sum(ap)
    #     else:
    #         aps = 0
    #     op = [s[1] for s in pos_ratios if s[0] in object_pos]
    #     if op:
    #         ops = sum(op)
    #     else:
    #         ops = 1 #avoid divide zero error - only happens with aps of 1
    #         #print("aps",aps,"ops",ops)
    #     return aps/ops

######## REFLEXIVE EXPRESSION ANALYSIS FUNCTIONS

    #checked
    def analyse_reflexive_expressions(self,df,s3:session.S3,comprehend):
        #self.__bucket_name = s3_bucket_name
        text_series = df.text.replace('\r\n','\n') # Comprehend treats \r\n as one character
        # Upload reflections to S3 for analysis
        s3.upload_docs(text_series)
        
        # Save a copy of reflections locally for offline analysis
        self.save_docs(text_series)

        # Submit the job
        return comprehend.submit_custom_entity_job("reflexive_expressions_analysis") #submitReflexiveExpressionsJob(access_role_arn, entity_recogniser_arn)
    
    #checked
    def save_docs(self,text_series,):
        logger.info(f"Saving {len(text_series)} docs to {self.config.local_path}...")
        for idx in text_series.index:
            file_name = f"{self.config.prefix}{idx}.txt"
            file_body = text_series.iloc[idx]
            logger.info(f"Saving {file_name}")
            with open(f"{self.config.local_path}{file_name}",'w') as fp:
                fp.write(file_body) 
        logger.info("Finished saving reflections locally.")
    



    #checked
    def extractAnalysisFromResults(self,results):
        analysis_output = dict()
        jresults = json.loads(results)
        for result in jresults:
            j = json.loads(result)
            #print(j)
            idx = j["File"].split('_')[-1].split('.')[0]
            analysis_output[int(idx)] = j["Entities"]
        return analysis_output

    #checked
    def add_to_dataframe(self,df,results):
        # Extract analysis from raw results
        analysis_output = self.extractAnalysisFromResults(results)
        # Add results to dataframe
        results_df = df.copy()
        results_df['ReflexiveResults'] = pd.Series(analysis_output)
        return results_df

    #--
    def reflexive_analytics(self,df):
        #util = Util()
        custom_df = df.copy() 
        # custom_df["text_length"] = df.text.apply(lambda x: len(x))
        # if (len(custom_df)>1):
        #     custom_df["text_scaled"] = util.scale_min_max(custom_df[['text_length']])
        # else:
        #     custom_df["text_scaled"] = 1
        #custom_df["reflexive_results"] = df.reflexiveResults
        # The expressions and their reflexive expression labels
        custom_df["reflexive_expressions"] = df.ReflexiveResults.apply(self.parse_reflexiveResults)
        # The counts for each labels
        custom_df["reflexive_counts"] = custom_df.reflexive_expressions.apply(util.count_labels)
        # Ratios between reflexive expressions
        custom_df["reflexive_ratio"] = custom_df.reflexive_counts.apply(util.ratios)
        # Ratio vector
        custom_df['ratio_vector'] = custom_df.reflexive_ratio.apply(self.make_ratio_vector)
        # Get the diversity of reflexive types - out of 8 possible types
        custom_df["reflexive_type_diversity"] = custom_df.reflexive_counts.apply(lambda x: len(x)/8)
        # A total of all labels
        custom_df["reflexive_total"] = custom_df.reflexive_counts.apply(util.tuple_values_total)
        # MinMax scale the reflexive_total
        if (len(custom_df)>1):
            custom_df["reflexive_scaled"] = util.scale_min_max(custom_df[['reflexive_total']])
        else:
            custom_df["reflexive_scaled"] = 1
        # Normalise based on text_scaled
        custom_df['reflexive_norm'] = util.normalise_scaled(custom_df,'reflexive_scaled')
        return custom_df

    #checked
    # Parse reflexive results - include all above threshold
    def parse_reflexiveResults(self,reflexiveResults,threshold=0.5):
        final_refs = list()
        #rr = json.loads(reflexiveResults)
        for ref in reflexiveResults:
            if ref['Score'] > threshold:
                final_refs.append((str.lower(ref['Text']),ref['Type']))
        return final_refs
    
    #--
    # Function for creating a vector out of reflexive ratio - could be used for others
    def make_ratio_vector(self,ratio_list,ref_codes = ['RR','ER','VR','AR','EP','AF','CN','EV']):
        ratio_dict = dict(ratio_list)
        vec = []
        for rc in ref_codes:
            if rc in ratio_dict.keys():
                vec.append(ratio_dict[rc])
            else:
                vec.append(0)
        return vec