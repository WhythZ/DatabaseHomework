# DatabaseHomework

## License
This repo adopts [MIT License](https://spdx.org/licenses/MIT)

## About
This repo stores a minimal implementation for the school's database course, we're forced to use OpenGuass instead of other DBMS

## Deployment
- Clone this repo locally (no need to import into the docker container), supposed the folder name to be `DatabaseHomework`

```bash
git clone git@github.com:WhythZ/DatabaseHomework.git
```

- Install the library dependencies in `requirements.txt`

```bash
cd xxx/xxx/DatabaseHomework
pip install -r requirements.txt
```

- Start your OpenGauss environment, you can create a docker container of OpenGauss (after you pulled the corresponding docker image) using following commands

```bash
docker run --name DatabaseHomework --privileged=true -d -e GS_PASSWORD=StrongPassword@1234567890 -p 8888:5432 opengauss/opengauss-server:latest
```

- Edit the `config.py` settings according to your own environment and settings

```py
DB_CONFIG = {
    "host": "localhost",
    # Use the left port of `docker run -p` parameter
    "port": 8888,
    "database": "postgres",
    "user": "gaussdb",
    # Keep the same as the `GS_PASSWORD` parameter
    "password": "StrongPassword@1234567890"
}
```

- Enter your Python virtual environment, for example conda here

```bash
conda create -n DBH python=3.10
conda activate DBH
```

- Enter the `Codes` folder to run the `init.py` script to initialize the structure and contents of database for the homework

```bash
cd Codes
python init.py
```

- Run `app.py`, then visit the generated link in browser to get access to the system

```bash
streamlit run app.py
```