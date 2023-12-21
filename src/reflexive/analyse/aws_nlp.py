

from reflexive.common.parameters import Parameters
from reflexive.common.local import Local
from reflexive.aws_connect.comprehend import Comprehend
from reflexive.common.util import Util

import json
import logging
import pandas as pd

try:
    import coloredlogs
    coloredlogs.install(level='INFO')
except:
    print("Colored logs not available")

class Nlp:
    
    logger = logging.getLogger(__name__)
    
    def __init__(self,parameters:Parameters,local:Local,comprehend:Comprehend):
        self.__parameters = parameters.all_parameters()
        self.logger.debug(f"Parameters: {self.__parameters}")
        self.local_path = self.__parameters['local_path']
        self.prefix = self.__parameters['prefix']
        self.postfix = self.__parameters['postfix']
        self.analysis_types = self.__parameters['analysis_types']
        self.__local = local
        self.__comprehend = comprehend



    #### COMPREHEND ANALYSIS

    def comprehend_analysis(self,df):
        util = Util()
        comprehend = self.__comprehend
        self.analysis_types = self.__parameters['analysis_types']
        #print(type(df.text))
        # chunk the text for batch analysis
        chunked_text = util.series_to_chunked_list(series=df.text)
        print("Number of chunks:",len(chunked_text))
        # start batch analysis
        chunked_results = comprehend.get_multiple_batch_analysis(chunked_text)
        print("Finished Analysis.")
        # write to file
        print("Writing data to file...")
        with open(f"{self.local_path}{self.prefix}analysis_chunks{self.postfix}.json", "w") as fp:
            json.dump(chunked_results,fp)            
        print("DONE!")
        # unchunk
        final_results = {}
        for key in chunked_results.keys():
            final_results[key] = comprehend.unbatch_results(self.analysis_types[key],chunked_results[key])
            print("Finished Unbatching",key," -  Writing data to file...")
            filename = f"{self.local_path}{self.prefix}{key}{self.postfix}.json"
            with open(filename, "w") as fp:
                json.dump(final_results[key],fp)            
        print("DONE!")
        # Save final_results for reload if necessary
        with open(f"{self.local_path}{self.prefix}final_results{self.postfix}.json", "w") as fp:
            json.dump(final_results,fp) 
        return final_results
    
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
    
    def add_results_to_df(self,results,df):
        for key in results.keys():
            rs = results[key]['results']
            newresults = {}
            for oldkey in rs.keys():
                newresults[int(oldkey)] = rs[oldkey] # Need to change keys to int to properly add to dataframe
            df[key] = pd.Series(newresults)
        return df
    
    def nlp_analytics(self,df):
        temp_df = df.copy()
        temp_df = self.keyphrase_analytics(temp_df)
        temp_df = self.named_entity_analytics(temp_df)
        temp_df = self.targeted_sentiment_analytics(temp_df)
        temp_df = self.syntax_analytics(temp_df)
        return temp_df
    
    
    def keyphrase_analytics(self,df):
        util = Util()
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
    
    def named_entity_analytics(self,df):
        util = Util()
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
    
    def targeted_sentiment_analytics(self,df):
        util = Util()
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
    
    def syntax_analytics(self,df):
        util = Util()
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
    
    
    # Parse key_phrases results - include all above threshold
    def parse_keyPhraseResults(self,keyPhraseResults,threshold=0.95,min_count=1):
        util = Util()
        phrases = {}
        filtered = [str.lower(r['Text']) for r in keyPhraseResults if r['Score'] > threshold]
        for phrase in filtered:
            phrases[phrase] = phrases.get(phrase,0)+1

        filtered_phrases = {k:v for k,v in phrases.items() if v >= min_count}
        return util.sort_dict_by_value(filtered_phrases)

    # Parse syntax results - include specific postags
    def parse_syntaxResults(self,syntax_results,postags_keep = ['ADV','VERB','AUX','ADJ','NOUN','PRON','PROPN']):
        sequence = list()
        for token in syntax_results:
            tag = token['PartOfSpeech']['Tag']
            if tag in postags_keep:
                sequence.append((str.lower(token['Text']),tag))
        return sequence

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

