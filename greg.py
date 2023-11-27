"""Test pipeline to exercise various data flow mechanisms."""
import kfp
from kfp_tekton.compiler import TektonCompiler
from kfp_tekton.compiler.pipeline_utils import TektonPipelineConf

"""Producer"""
def send_file(
    outgoingfile: kfp.components.OutputPath(),
):
    import urllib.request

    print("starting download...")
    urllib.request.urlretrieve("http://212.183.159.230/20MB.zip", outgoingfile)
    print("done")

"""Consumer"""
def receive_file(
    incomingfile: kfp.components.InputPath(),
    saveartifact: kfp.components.OutputPath("saveartifact"),
):
    import os
    import shutil

    print("reading %s, size is %s" % (incomingfile, os.path.getsize(incomingfile)))

    with open(incomingfile, "rb") as f:
        b = f.read(1)
        print("read byte: %s" % b)
        f.close()
    
    print("copying in %s to out %s" % (incomingfile, saveartifact))
    shutil.copyfile(incomingfile, saveartifact)


"""Build the producer component"""
send_file_op = kfp.components.create_component_from_func(
    send_file,
    base_image="registry.access.redhat.com/ubi8/python-38",
)

"""Build the consumer component"""
receive_file_op = kfp.components.create_component_from_func(
    receive_file,
    base_image="registry.access.redhat.com/ubi8/python-38",
)


"""Wire up the pipeline"""
@kfp.dsl.pipeline(
    name="Test Data Passing Pipeline 1",
)
def wire_up_pipeline():
    import json

    send_file_task = send_file_op()

    receive_file_task = receive_file_op(
        send_file_task.output,
    ).add_pod_annotation(name='artifact_outputs', value=json.dumps(['saveartifact']))


if __name__ == "__main__":
    conf = TektonPipelineConf()
    conf.bash_image_name = 'ubi8/python-39'
    conf.condition_image_name = 'ubi8/python-39'
    TektonCompiler().compile(
        pipeline_func=wire_up_pipeline,
        package_path=__file__.replace(".py", ".yaml"),
        tekton_pipeline_conf=conf
    )