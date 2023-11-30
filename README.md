A very quick technical demo: https://youtu.be/l0SrSRmibwM

## Noteboook notes

if using 2023.2 TF, need: `!pip install "onnx==1.14.1"`

## Notes

docker buildx build --platform linux/amd64 -t quay.io/mmortari/rdsp:latest --push .

## Running notes

curl --silent -X 'GET' \
  "$MR_HOSTNAME/api/model_registry/v1alpha1/registered_models?pageSize=100&orderBy=ID&sortOrder=DESC&nextPageToken=" \
  -H 'accept: application/json' | jq .items

curl --silent -X 'GET' \
  "$MR_HOSTNAME/api/model_registry/v1alpha1/model_versions?pageSize=100&orderBy=ID&sortOrder=DESC&nextPageToken=" \
  -H 'accept: application/json' | jq .items

curl --silent -X 'GET' \
  "$MR_HOSTNAME/api/model_registry/v1alpha1/serving_environments?pageSize=100&orderBy=ID&sortOrder=DESC&nextPageToken=" \
  -H 'accept: application/json' | jq .items

curl -X 'POST' \
  $MR_HOSTNAME'/api/model_registry/v1alpha1/serving_environments/1/inference_services' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "name": "mnist-e2e-se3",
  "modelVersionId": "3",
  "runtime": "mmserver1",
  "registeredModelId": "2",
  "servingEnvironmentId": "1",
  "state": "DEPLOYED"
}'

curl -X 'PATCH' \
  "$MR_HOSTNAME/api/model_registry/v1alpha1/inference_services/7" \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "modelVersionId": "3",
  "runtime": "mmserver1",
  "state": "UNDEPLOYED"
}'

curl --silent -X 'GET' \
  "$MR_HOSTNAME/api/model_registry/v1alpha1/inference_services/5/serves?pageSize=100&orderBy=ID&sortOrder=DESC&nextPageToken=" \
  -H 'accept: application/json' | jq
