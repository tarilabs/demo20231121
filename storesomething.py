import kfp
from kfp_tekton.compiler import TektonCompiler

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

    def save_pickle(object_file, target_object):
        with open(object_file, "w") as f:
            json.dump(target_object, f)
            
    save_pickle(model_file, model)

create_step_os_environ_print = kfp.components.create_component_from_func(
    func=os_environ_print,
    base_image='ubi8/python-39',
    packages_to_install=[])

@kfp.dsl.pipeline(
    name="Test Matteo storesomething",
)
def my_pipeline(my_input):
  import json
  task1 = create_step_os_environ_print(
      my_input=my_input, 
      input2=kfp.dsl.RUN_ID_PLACEHOLDER
    ).add_pod_annotation(name='artifact_outputs', value=json.dumps(['model_file']))


if __name__ == "__main__":
    TektonCompiler().compile(
        my_pipeline, __file__.replace(".py", ".yaml")
    )