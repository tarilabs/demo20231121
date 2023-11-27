import kfp
from kfp_tekton.compiler import TektonCompiler
from kubernetes.client.models import V1EnvVar
import json
import re

def step1(my_input, input2, outgoingfile: kfp.components.OutputPath("model_file")):
    import os
    import pickle
    import json
    model = dict()
    model['my_input'] = my_input
    model['input2'] = input2
    model['osenviron'] = json.dumps(dict(os.environ))
    print(model)
    print(outgoingfile)

    from tensorflow import keras
    (X_train,y_train),(X_test,y_test) = keras.datasets.mnist.load_data()

    X_train = X_train/255
    X_test = X_test/255
    print('y_train[7] is the label:', y_train[7])

    def save_pickle(object_file, target_object):
        with open(object_file, "w") as f:
            json.dump(target_object, f)
            
    save_pickle(outgoingfile, model)


def step2(incomingfile: kfp.components.InputPath("model_file"), saveartifact: kfp.components.OutputPath("saveartifact")):
    import shutil
    print(f'incomingfile: {incomingfile}')
    with open(incomingfile, 'r') as reader:
        for line in reader:
            print(line)
    shutil.copyfile(incomingfile, saveartifact)
    print('end.')


def logg_env_function():
  import os
  import logging
  logging.basicConfig(level=logging.INFO)
  logging.info(os.environ)


create_step1 = kfp.components.create_component_from_func(
    func=step1,
    base_image='quay.io/mmortari/rdsp:latest',
    packages_to_install=[])

create_step2 = kfp.components.create_component_from_func(
    func=step2,
    base_image='quay.io/mmortari/rdsp:latest')


logg_env_function_op = kfp.components.func_to_container_op(logg_env_function,
                                                 base_image='registry.access.redhat.com/ubi8/python-39')


@kfp.dsl.pipeline(
    name="Test Matteo storesomething",
    description='I need to store on S3, I need to know which location in the bucket, I need to know the name of the S3 bucket'
)
def my_pipeline(my_input):
  bucket = 'mybucket'
  env_var = V1EnvVar(name='AWS_SECRET_ACCESS_KEY', value_from={'secretKeyRef': {'name': f'aws-connection-{bucket}', 'key': 'AWS_SECRET_ACCESS_KEY'}})
  task0 = logg_env_function_op().add_env_variable(env_var) 
  task1 = create_step1(
      my_input=my_input, 
      input2=kfp.dsl.RUN_ID_PLACEHOLDER
    ).add_pod_annotation(name='artifact_outputs', value=json.dumps(['model_file']))
  task2 = create_step2(incomingfile=task1.output).add_pod_annotation(name='artifact_outputs', value=json.dumps(['saveartifact']))


if __name__ == "__main__":
    TektonCompiler().compile(
        my_pipeline, __file__.replace(".py", ".yaml")
    )
    # problem: each pipeline step pod contains other auxiliary pods for copying artifacts to object store that uses busybox, and these ones aren't possible to change through code
    outYaml = __file__.replace(".py", ".yaml")
    with open(outYaml, 'r') as file:
        content = file.read()
    pattern = re.compile(r'image: busybox')
    modified_content = pattern.sub('image: registry.access.redhat.com/ubi8/python-38', content)
    pattern = re.compile(r'storageClassName: kfp-csi-s3')
    modified_content = pattern.sub('storageClassName: standard-csi', modified_content)
    pattern = re.compile(r'apiVersion: tekton.dev/v1')
    modified_content = pattern.sub('apiVersion: tekton.dev/v1beta1', modified_content)
    with open(outYaml, 'w') as file:
        file.write(modified_content)