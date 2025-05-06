{ pkgs ? import <nixpkgs> {} }:

let
  pythonEnv = pkgs.python312.withPackages (ps: with ps; [
    asgiref
    bcrypt
    certifi
    cffi
    chardet
    cryptography
    django
    django-cors-headers
    djangorestframework
    gunicorn
    idna
    markdown
    packaging
    paramiko
    pillow
    psycopg2
    pycparser
    pyjwt
    pynacl
    python-dotenv
    pytz
    requests
    six
    soupsieve
    sqlparse
    typing-extensions
    urllib3
    whitenoise
  ]);
in
  pythonEnv