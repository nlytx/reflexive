
import os
import logging,coloredlogs
#import boto3
import pandas as pd

from reflexive.common.parameters import Parameters

coloredlogs.install(level='INFO')

class Local:
    
    logger = logging.getLogger(__name__)
    
    def __init__(self,parameters:Parameters):
        self.__parameters = parameters.all_parameters()
        self.logger.debug(f"Parameters: {self.__parameters}")
        self.local_path = self.__parameters['local_path']
        self.local_dir = self.local_path
        self.logger.info(f"Path: {self.local_path}")
        self.prefix = self.__parameters['prefix']
        self.postfix = self.__parameters['postfix']
        
    def get_data_path_name(self,name,ext):
        return f"{self.local_path}{self.prefix}{name}{self.postfix}.{ext}"
        
    def set_sub_dir(self,sub_dir=None):
        # check dir sub_dir exists
        if sub_dir:
            self.local_dir = f"{self.local_path}{sub_dir}/"
            self.logger.debug(f"local_dir: {self.local_dir}")
            dirExists = os.path.exists(self.local_dir)
            if not dirExists:
                self.logger.info(f"Creating subdirectory: {self.local_dir}")
                os.makedirs(self.local_dir)
        else:
            self.local_dir = self.local_path
        
    def save_docs(self,text_series,):
        self.logger.info(f"Saving {len(text_series)} docs to {self.local_dir}...")
        for idx in text_series.index:
            file_name = f"{self.prefix}{idx}.txt"
            file_body = text_series.iloc[idx]
            self.logger.info(f"Saving {file_name}")
            with open(f"{self.local_dir}{file_name}",'w') as fp:
                fp.write(file_body) 
        self.logger.info("Finished saving reflections locally.")
        
