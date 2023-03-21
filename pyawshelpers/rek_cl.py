import time
import boto3

from progress.spinner import LineSpinner

class AWSRekCl(object):
    __client = None
    __logger = None

    def __init__(self, reko_client:boto3.client, region, logger=None):

        self.__logger = logger
        self.__client = reko_client
        self.__region = region

    def rek_cl_get_project(self,project_name, rek_client = None):
        """Rekognition Custom Label : Create or get project"""
        if rek_client == None:
            rek_client = self.__client
        try:
            cl_project = rek_client.create_project(
                ProjectName=project_name
            )
        except self.__client.exceptions.ResourceInUseException:
            # Describe rekognition project
            cl_projects = rek_client.describe_projects(
                ProjectNames=[project_name]
            )
            cl_project = cl_projects['ProjectDescriptions'][0]
        return cl_project


    def rek_cl_create_dataset(self, project_name, manifest_bucket, manifest_key):
        """Rekognition Custom Label : Delete and create Datasets TRAIN and TEST"""
        # Describe rekognition project
        cl_projects = self.__client.describe_projects(
            ProjectNames=[project_name]
        )
        cl_project = cl_projects['ProjectDescriptions'][0]
        # Delete existing dataset
        for dataset in cl_project['Datasets']: 
            try:
                self.__client.delete_dataset(DatasetArn=dataset['DatasetArn'])
            except self.__client.exceptions.ResourceNotFoundException:
                print('dataset already deleted')
        cl_dataset_train = self.__client.create_dataset(
                            DatasetSource={
                                'GroundTruthManifest': {
                                    'S3Object': {
                                        'Bucket': manifest_bucket,
                                        'Name': manifest_key
                                    }
                                }
                            },
                            DatasetType='TRAIN',
                            ProjectArn=cl_project['ProjectArn']
                        )

        ## Wait for the creation of the train dataset to complete
        chk_status = True
        starttime = time.time()
        spinner = LineSpinner('Creating Train dataset')
        while (chk_status):
            spinner.next()
            time.sleep (30)
            dataset_status = self.__client.describe_dataset(
                                DatasetArn=cl_dataset_train['DatasetArn']
                            )
            if ( (dataset_status['DatasetDescription']['Status'] != 'CREATE_IN_PROGRESS') ):
                chk_status = False
            ## Continue to check for status for 1 hour
            if ((time.time() - starttime) > 3600):
                chk_status = False
                
        cl_dataset_test = self.__client.create_dataset(
                    DatasetType='TEST',
                    ProjectArn=cl_project['ProjectArn']
                )
        ## Wait for the creation of the empty test dataset to complete
        chk_status = True
        starttime = time.time()
        spinner = LineSpinner('Creating Test dataset')
        while (chk_status):
            spinner.next()
            time.sleep (30)
            dataset_status = self.__client.describe_dataset(
                                    DatasetArn=cl_dataset_test['DatasetArn']
                                )
            if ( (dataset_status['DatasetDescription']['Status'] != 'CREATE_IN_PROGRESS') ):
                chk_status = False
            ## Continue to check for status for 1 hour
            if ((time.time() - starttime) > 3600):
                chk_status = False
                # Raise an exception if needed
        
        ## Split the dataset that was created earlier into Training and Test dataset
        cl_distribute_dataset = self.__client.distribute_dataset_entries(
            Datasets=[
                {
                    'Arn': cl_dataset_train['DatasetArn']
                },
                {
                    'Arn': cl_dataset_test['DatasetArn']
                }
            ]
        )
        ## Wait for the splitting of the dataset to complete
        chk_status = True
        starttime = time.time()
        spinner = LineSpinner('Distributing dataset entries')
        while (chk_status):
            spinner.next()
            time.sleep (30)
            dataset_status_train = self.__client.describe_dataset(
                                        DatasetArn=cl_dataset_train['DatasetArn']
                                    )
            dataset_status_test = self.__client.describe_dataset(
                                        DatasetArn=cl_dataset_test['DatasetArn']
                                    )
            if ( (dataset_status_train['DatasetDescription']['Status'] != 'CREATE_IN_PROGRESS') and (dataset_status_test['DatasetDescription']['Status'] != 'CREATE_IN_PROGRESS') ):
                chk_status = False
            ## Continue to check for status for 1 hour
            if ((time.time() - starttime) > 3600):
                chk_status = False
                # Raise an exception if needed

    def rek_cl_create_project_version(self,project_name,model_bucket, model_key):
        """Rekognition Custom Label : Create a new project version, tran and start model"""
        ## Start Training the model
        model_version_name = f'model_v{str(int(time.time()))}'
        cl_project = self.rek_cl_get_project(self,project_name)
        cl_project_version = self.__client.create_project_version(
            ProjectArn=cl_project['ProjectArn'],
            VersionName=model_version_name,
            OutputConfig={
                'S3Bucket': model_bucket,
                'S3KeyPrefix': model_key + 'model_train'
            }
        )
        ## Wait for the training to finish. This may take 2 to 4 hours
        chk_status = True
        starttime = time.time()
        spinner = LineSpinner('Project training')
        while (chk_status):
            ## wait for 30 minute. To check status every 30 minutes
            spinner.next()
            time.sleep (60)
            model_traing_status = self.__client.describe_project_versions(
                                        ProjectArn=cl_project['ProjectArn'],
                                        VersionNames=[
                                                    model_version_name
                                                    ]
                
                                    )
            if ( (model_traing_status['ProjectVersionDescriptions'][0]['Status'] != 'TRAINING_IN_PROGRESS') ):
                chk_status = False
            ## Continue to check for status for 10 hour
            if ((time.time() - starttime) > 36000):
                chk_status = False
                # Raise an exception if needed
        
        ## Model metrics
        model_metrics = self.__client.describe_project_versions(
            ProjectArn=cl_project['ProjectArn'],
            VersionNames=[
                            model_version_name
                        ]

        )
        print ("F1 Score " + str(model_metrics['ProjectVersionDescriptions'][0]['EvaluationResult']['F1Score']))
        start_model = self.__client.start_project_version(
            ProjectVersionArn=cl_project_version['ProjectVersionArn'],
            MinInferenceUnits=1
        )

        ## Wait for the model to start
        chk_status = True
        starttime = time.time()
        spinner = LineSpinner('Starting model')
        while (chk_status):
            spinner.next()
            time.sleep (60)
            model_start_status = self.__client.describe_project_versions(
                                        ProjectArn=cl_project['ProjectArn'],
                                        VersionNames=[
                                                    model_version_name
                                                    ]
                
                                    )
            if ( (model_start_status['ProjectVersionDescriptions'][0]['Status'] != 'STARTING') ):
                chk_status = False
            ## Continue to check for status for 1 hour
            if ((time.time() - starttime) > 3600):
                chk_status = False
                # Raise an exception if needed
        print(model_start_status)
        return cl_project_version

    def rek_cl_copy_project_version(self, client_destination, project_name, cl_project_version_source, model_bucket_destination, model_key_destination):
        """Rekognition Custom Label : Copy and start a project version"""
        model_version_name = f'model_v{str(int(time.time()))}'
        cl_project_destination = self.rek_cl_get_project(project_name = project_name, rek_client=client_destination)
        cl_project_source = self.rek_cl_get_project(project_name)

        cl_project_version =  client_destination.copy_project_version(
            DestinationProjectArn=cl_project_destination['ProjectArn'],
            OutputConfig = {
                "S3Bucket": model_bucket_destination,
                "S3KeyPrefix": model_key_destination
            },
            SourceProjectArn = cl_project_source['ProjectArn'],
            SourceProjectVersionArn = cl_project_version_source['ProjectVersionArn'],
            VersionName = model_version_name
        )
        ## Wait for the model to copy
        chk_status = True
        starttime = time.time()
        spinner = LineSpinner('Copying model')
        while (chk_status):
            spinner.next()
            time.sleep (30)
            model_copy_status = client_destination.describe_project_versions(
                                        ProjectArn=cl_project_destination['ProjectArn'],
                                        VersionNames=[
                                                    model_version_name
                                                    ]          
                                    )
            if ( (model_copy_status['ProjectVersionDescriptions'][0]['Status'] != 'COPYING') ):
                chk_status = False
            ## Continue to check for status for 1 hour
            if ((time.time() - starttime) > 3600):
                chk_status = False
                # Raise an exception if needed
        print(model_copy_status)

        start_model = client_destination.start_project_version(
                ProjectVersionArn=cl_project_destination['ProjectArn'],
                MinInferenceUnits=2
        )

        ## Wait for the model to start
        chk_status = True
        starttime = time.time()
        spinner = LineSpinner('Starting model')
        while (chk_status):
            spinner.next()
            time.sleep (30)
            model_start_status = client_destination.describe_project_versions(
                                        ProjectArn=cl_project_destination['ProjectArn'],
                                        VersionNames=[
                                                    model_version_name
                                                    ]
                
                                    )
            if ( (model_start_status['ProjectVersionDescriptions'][0]['Status'] != 'STARTING') ):
                chk_status = False
            ## Continue to check for status for 1 hour
            if ((time.time() - starttime) > 3600):
                chk_status = False
                # Raise an exception if needed
        print(model_start_status)
        return cl_project_version

