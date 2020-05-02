### Introduction
The `google_paa.py` script crawls the question and answer from People Also Asked section using selenium webdriver.  

Since there is no API for Google's PAA (people also asked) section, we will use selenium to automate browsers. We can specify the number of questions we want to crawl for job titles. This script will output one csv file (whether only 1 job title is passed or multiple). The example of output is posted in the 1st comment below.

The running time for querying "software engineer" with 20 PAA question-answer pairs 
is 50 seconds with the default settings. 


### Environment requirements
#### chrome drivers  
please download the drivers with the correct Chrome version and 
OS system that your workstation has from the official page [here](https://chromedriver.chromium.org/downloads).
And place it under the `driver` subfolder. 
Rename the driver by adding your OS to the end, e.g.`chromedriver_mac` for MacOS and `chromedriver_linux` for Linux based OS.
<br>To find the version of your Chrome browser, visit `chrome://version/` in your Chrome.
#### python dependencies  
There are 2 ways to set up the environment and manage the dependencies:
1. use [poetry](https://python-poetry.org/) <-- recommended
2. use any other virtual environment tool you like, such as conda or virtualenv. Please refer to the `requirements.txt` and make sure the listed packages are installed.
If not, just run `pip install -r requirements.txt` to install them.

### To run
An example command line usage:
```bash
python google_paa.py query "software engineer" \
    --output_paa="output/paa_software+engineer.csv" \
    --output_fs="output/fs_software+engineer.csv" \
    --headless \
    --cleantext \
    --num=30
```

Type `python google_paa.py -h` to see the full usage documentation.
 
```