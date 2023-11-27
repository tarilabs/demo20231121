import kfp
from kfp_tekton.compiler import TektonCompiler
from kubernetes.client.models import V1EnvVar
import json

def os_environ_print(my_input, input2, model_file: kfp.components.OutputPath("model_file"),):
    import os
    import pickle
    import json
    model = dict()
    model['my_input'] = my_input
    model['input2'] = input2
    model['osenviron'] = json.dumps(dict(os.environ))
    print(model)
    print(model_file)

    from tensorflow import keras
    (X_train,y_train),(X_test,y_test) = keras.datasets.mnist.load_data()

    X_train = X_train/255
    X_test = X_test/255
    print('y_train[7] is the label:', y_train[7])

    def save_pickle(object_file, target_object):
        with open(object_file, "w") as f:
            json.dump(target_object, f)
            
    save_pickle(model_file, model)


def logg_env_function():
  import os
  import logging
  logging.basicConfig(level=logging.INFO)
  logging.info(os.environ)


create_step_os_environ_print = kfp.components.create_component_from_func(
    func=os_environ_print,
    base_image='quay.io/mmortari/rdsp:latest',
    packages_to_install=[])


logg_env_function_op = kfp.components.func_to_container_op(logg_env_function,
                                                 base_image='ubi8/python-39')


@kfp.dsl.pipeline(
    name="Test Matteo storesomething",
    description='I need to store on S3, I need to know which location in the bucket, I need to know the name of the S3 bucket'
)
def my_pipeline(my_input):
  bucket = 'mybucket'
  env_var = V1EnvVar(name='AWS_SECRET_ACCESS_KEY', value_from={'secretKeyRef': {'name': f'aws-connection-{bucket}', 'key': 'AWS_SECRET_ACCESS_KEY'}})
  task0 = logg_env_function_op().add_env_variable(env_var) 
  task1 = create_step_os_environ_print(
      my_input=my_input, 
      input2=kfp.dsl.RUN_ID_PLACEHOLDER
    ).add_pod_annotation(name='artifact_outputs', value=json.dumps(['model_file']))


if __name__ == "__main__":
    TektonCompiler().compile(
        my_pipeline, __file__.replace(".py", ".yaml")
    )