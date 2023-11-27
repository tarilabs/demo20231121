## This image support pipeline tasks with MR client installed

FROM registry.access.redhat.com/ubi8/python-39

COPY model_registry-0.1.0-py3-none-any.whl /app/
RUN pip install "tensorflow==2.11"
RUN pip install "ml-metadata==1.14.0"
RUN pip install /app/model_registry-0.1.0-py3-none-any.whl
RUN pip install "protobuf==3.20.3"
RUN pip install "tf2onnx==1.14.0"
RUN pip install onnxruntime
RUN pip install boto3
