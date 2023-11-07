
#from spacy import displacy

#from reflexive.common.parameters import Parameters

import logging
try:
    import coloredlogs
    coloredlogs.install(level='INFO')
except:
    print("Colored logs not available")

class Display:
    
    logger = logging.getLogger(__name__)
    
    def __init__(self): #,parameters:Parameters):
        self.name="Display"
        self.priority_tags = ["AR","EP","VR_EV_CN","ER_AF","RR","KP"]
        self.colours = {"VR_EV_CN": "#ff6644","ER_AF": "#dd44cc","AR": "#00cc00","EP": "#aacc33","RR": "#00aaff","KP":"#aaaacc"}
        self.options = {"ents": ["VR_EV_CN","ER_AF","AR","EP","RR","KP"], "colors": self.colours}
        


    def add_reflexive_offsets(self,df):
        temp_df = df.copy()
        temp_df['reflexive_offsets'] = temp_df.reflexiveResults.apply(self.collect_reflexive_offsets)
        return temp_df
        
    def add_keyphrase_offsets(self,df):
        temp_df = df.copy()
        temp_df['keyphrase_offsets'] = temp_df.KeyPhraseResults.apply(self.collect_keyphrase_offsets)
        return temp_df
    
    def add_offsets(self,df):
        df = self.add_reflexive_offsets(df)
        return self.add_keyphrase_offsets(df)
    
    def create_displacy(self,df):
        all_ents = list(df.apply(self.render_record,axis=1))
        #html_out = displacy.render(all_ents,manual=True,style="ent", options=options,page=True,jupyter=False)
        # with open(f"{path}{prefix}annotated_reflections{postfix}.html","w") as fp:
        #     fp.write(html_out)
        #displacy.render(all_ents,manual=True,style="ent", options=options)
        return all_ents
            
    def render_record(self,record,title="----"):
        #timestamp = record['timestamp'].split('T')[0]
        #pseudonym = record['pseudonym']
        #point_round = record['point_round']
        #title = f"{pseudonym} ({point_round}) - {timestamp}"
        tags = self.priority_tags
        text = record['text']
        reflexive_offsets = record['reflexive_offsets']
        keyphrase_offsets = record['keyphrase_offsets']
        ents = []
        taken = []
        offsets = []
        for tag in tags:
            if tag in reflexive_offsets:
                offsets = reflexive_offsets[tag]
            elif tag in keyphrase_offsets:
                offsets = keyphrase_offsets[tag]
            
            for off in offsets:
                new_ent = {}
                if off[0] in taken:
                    # the start offset is taken
                    x = None
                elif off[1] in taken:
                    # the end offset is taken
                    x = None
                else:
                    # both start and end is available
                    taken.append(off[0])
                    taken.append(off[1])
                    #print(taken)
                    new_ent["start"] = off[0]
                    new_ent["end"] = off[1]
                    new_ent["label"] = tag
                    ents.append(new_ent)

        text_ents = {
            "text": text, #.replace('\r\n','\n'),
            "ents": ents,
            "title": title
        }

        return text_ents
    
    def collect_keyphrase_offsets(self,krs):
        new_krs = {}
        for kr in krs:
            if kr['Score']>0.98:
                new_krs.setdefault("KP",[]).append((kr['BeginOffset'],kr['EndOffset']))
        return new_krs

    def collect_reflexive_offsets(self,rrs):
        new_rrs = {}
        for rr in rrs:
            if rr['Score']>0.5:
                ent_type = rr['Type']
                if ent_type in ['VR','EV','CN']:
                    label = "VR_EV_CN"
                elif ent_type in ['ER','AF']:
                    label = "ER_AF"
                else:
                    label = ent_type
                new_rrs.setdefault(label,[]).append((rr['BeginOffset'],rr['EndOffset']))
        return new_rrs