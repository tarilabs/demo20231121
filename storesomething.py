import kfp
from kfp_tekton.compiler import TektonCompiler
from kubernetes.client.models import V1EnvVar
import json
import re

def train_model(my_input, input2, outgoingfile: kfp.components.OutputPath("model_file"), outgoingfile2: kfp.components.OutputPath("onnx_file")):
    import os
    import shutil
    import pickle
    import json
    model = dict()
    model['my_input'] = my_input
    model['input2'] = input2
    model['osenviron'] = json.dumps(dict(os.environ))
    print(model)
    print(outgoingfile)

    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import Sequential
    (X_train,y_train),(X_test,y_test) = keras.datasets.mnist.load_data()

    X_train = X_train/255
    X_test = X_test/255
    print('y_train[7] is the label:', y_train[7])

    model = Sequential()
    model.add(tf.keras.layers.Conv2D(filters=32, kernel_size=(3, 3), input_shape=(28, 28, 1)))
    model.add(tf.keras.layers.MaxPooling2D(pool_size=(2, 2), strides=2))
    model.add(tf.keras.layers.Flatten())
    model.add(tf.keras.layers.Dense(units=64, activation=tf.nn.relu))
    model.add(tf.keras.layers.Dropout(rate=0.2))
    model.add(tf.keras.layers.Dense(10, activation=tf.nn.softmax))
    model.compile(optimizer='adam',
                loss='sparse_categorical_crossentropy',
                metrics=['accuracy'])
    print(model.summary())
    history = model.fit(X_train,y_train,epochs=3)
    import tf2onnx
    import onnx
    input_signature = [tf.TensorSpec([1, 28, 28], tf.double, name='x')]
    onnx_model, _ = tf2onnx.convert.from_keras(model, input_signature, opset=12)
    onnx.save(onnx_model, "model.onnx")

    def save_pickle(model, object_file):
        with open(object_file, "wb") as f:
            pickle.dump(model, f)
            
    save_pickle(model, outgoingfile)
    shutil.copyfile('model.onnx', outgoingfile2)


def validate_model(incomingfile: kfp.components.InputPath("model_file")) -> bool:
    # For demo purposes, always validate.
    return True


def when_not_validated():
    print("The model built by CI failed to match required Validation, hence won't be registered in Model Registry")


def index_on_ModelRegistry(incomingfile: kfp.components.InputPath("onnx_file"), saveartifact: kfp.components.OutputPath("saveartifact")):
    import onnx
    print(f'incomingfile: {incomingfile}')
    onnx_model = onnx.load(incomingfile)
    onnx.checker.check_model(onnx_model)

    print('end.')


def logg_env_function():
  import os
  import logging
  logging.basicConfig(level=logging.INFO)
  logging.info(os.environ)


create_step1 = kfp.components.create_component_from_func(
    func=train_model,
    base_image='image-registry.openshift-image-registry.svc:5000/odh/jupyter-tensorflow-notebook:2023.1',
    packages_to_install=[])

create_step2 = kfp.components.create_component_from_func(
    func=validate_model,
    base_image='image-registry.openshift-image-registry.svc:5000/odh/jupyter-tensorflow-notebook:2023.1')

create_step3 = kfp.components.create_component_from_func(
    func=index_on_ModelRegistry,
    base_image='quay.io/mmortari/rdsp:latest')

create_step_when_not_validated = kfp.components.create_component_from_func(
    func=when_not_validated,
    base_image='registry.access.redhat.com/ubi8/python-39')

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
    ).add_pod_annotation(name='artifact_outputs', value=json.dumps(['model_file', 'onnx_file']))
  task2 = create_step2(incomingfile=task1.outputs['outgoingfile'])

  with kfp.dsl.Condition(task2.output == True):
      create_step3(incomingfile=task1.outputs['outgoingfile2']).add_pod_annotation(name='artifact_outputs', value=json.dumps(['saveartifact']))

  with kfp.dsl.Condition(task2.output == False):
      create_step_when_not_validated()


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
    pattern = re.compile(r'image: python:3.9.17-alpine3.18')
    modified_content = pattern.sub('image: registry.access.redhat.com/ubi8/python-38', modified_content)
    with open(outYaml, 'w') as file:
        file.write(modified_content)