docker build -t zaim-to-monarch .
docker run --env-file ./.env -t zaim-to-monarch
docker tag zaim-to-monarch:latest kalutes/zaim-to-monarch:latest; docker push kalutes/zaim-to-monarch:latest
docker push kalutes/zaim-to-monarch:latest
