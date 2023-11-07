#

import logging,coloredlogs
import boto3
import pandas as pd
import tarfile
import json

from reflexive.common.parameters import Parameters

coloredlogs.install(level='INFO')

class S3:
    
    logger = logging.getLogger(__name__)
    
    def __init__(self,parameters:Parameters):
        #print(parameters)
        # set local parameters
        self.__parameters = parameters.all_parameters()
        self.logger.debug(f"Parameters: {self.__parameters}")
        self.region = self.__parameters['region']
        self.prefix = self.__parameters['prefix']
        self.postfix = self.__parameters['postfix']
        self.s3_access_point_arn = self.__parameters["s3_accesspoint_arn"]
        self.bucket_name = self.__parameters["bucket_name"]
        # create client
        try:
            self.logger.debug(f"Region:{self.region}")
            self.__s3_client = boto3.client(service_name='s3',region_name=self.region)
        except Exception as err:
            self.logger.error("Unable to create S3 client: ",err)
    
    
    # Return the S3 client
    def client(self):
        return self.__s3_client
    
     # Function to upload reflections to S3
    def upload_docs(self,text_series):
        #self.__prefix, self.__postfix
        files_folder = f"{self.prefix}files{self.postfix}"

        s3 = self.__s3_client
        s3ap = self.s3_access_point_arn
        self.logger.debug(f"ACCESS POINT: {s3ap}")

        self.logger.info(f"Uploading {len(text_series)} reflections to S3 ({files_folder})...")
        self.logger.debug(f"({s3ap}/{files_folder})")
        for idx in text_series.index:
            file_name = f"{self.prefix}{idx}.txt"
            file_body = text_series.iloc[idx]
            self.logger.info(f"Uploading {file_name}")
            #print(file_body)
            response = s3.put_object(Body=file_body,Bucket=s3ap,Key=f"{files_folder}/{file_name}")
            if response['ResponseMetadata']['HTTPStatusCode'] != 200:
                self.logger.error("------------------------------------------------------------")
                self.logger.error(f"ERROR: There was a problem with {file_name}")
                self.logger.error(response)
                self.logger.error("------------------------------------------------------------")
            else:
                self.logger.info('Success')
        self.logger.info("Finished uploading reflections to S3.")
        return response
    
    # download and save results
    def results_download_save_extract(self,s3Uri,local_file_path):
        s3 = self.__s3_client
        output_key = s3Uri.split(self.bucket_name)[1]
        # download from S3 to local path
        with open(f"{local_file_path}.tar.gz",'wb') as output_data:
            s3.download_fileobj(self.bucket_name,output_key[1:],output_data)

        # extract the files from tar archive
        files = list()
        with tarfile.open(f"{local_file_path}.tar.gz", "r:gz") as tf:
            for member in tf.getmembers():
                f = tf.extractfile(member)
                if f is not None:
                    content = f.read()
                    files.append(content)
        #print("Number of files:",len(files))
        # extract results and save and return
        raw_results = files[0].decode("utf-8").split('\n')
        raw_results.pop() # pop last item off as empty entry due to final \n
        with open(f"{local_file_path}.json","w") as fp:
            fp.write(json.dumps(raw_results))
        return raw_results
        