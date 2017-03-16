FROM python:2-onbuild
EXPOSE 8066
CMD [ "python", "./IngestServer.py" ]
