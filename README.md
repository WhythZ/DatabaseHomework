# DatabaseHomework

## License
This repo adopts [MIT License](https://spdx.org/licenses/MIT)

## About
This repo stores a minimal implementation for the school's database course, we're forced to use OpenGuass instead of other DBMS

## Deployment
- Clone this repo to your computer as `DatabaseHomework` folder for example

```bash
git clone git@github.com:WhythZ/DatabaseHomework.git
```

- Create a new virtual environment and install the dependencies in `requirements.txt`

```bash
conda create -n DBH python=3.10
conda activate DBH

cd xxx/xxx/DatabaseHomework
pip install -r requirements.txt
```

- Create a new docker container of OpenGauss using following commands after pulling the corresponding docker image `opengauss-server`

```bash
docker run --name DBH --privileged=true -d -e GS_PASSWORD=StrongPassword@1234567890 -p 8888:5432 opengauss/opengauss-server:latest
```

- Edit the `config.py` configurations according to your own environment and settings

```py
DB_CONFIG = {
    "host": "localhost",
    # Use the left port of `docker run ... -p` parameter
    "port": 8888,
    "database": "postgres",
    "user": "gaussdb",
    # Keep the same as the `docker run ... GS_PASSWORD=` parameter
    "password": "StrongPassword@1234567890"
}
```

- Enter `Codes` folder to run `init.py` for initializing the contents required by the homework

```bash
cd Codes
python init.py
```

- Run `app.py` and visit the generated link in browser to get access to the system

```bash
streamlit run app.py
```