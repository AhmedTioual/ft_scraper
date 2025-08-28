# FT Scraper

**System Architecture:**  
![System Architecture](data/architecture/system_architecture.png)

FT Scraper is a Python-based project for automated extraction, transformation, and presentation of web-based content.

---

## Table of Contents

1. [Project Structure](#project-structure)  
2. [Installation](#installation)  
3. [Usage](#usage)  
4. [Automation](#Automation)  
---

## Project Structure

- `data/embeddings`: Stores text embeddings  
- `data/metadata`: JSON structures and metadata  
- `data/presentations`: Generated PPTX files  
- `ft_scraper/extract`: Fetch and search scripts  
- `ft_scraper/transform`: Data cleaning and preprocessing  
- `ft_scraper/load`: Database loading scripts  
- `ft_scraper/presentation`: Presentation generation  
- `ft_scraper/scheduler`: Scheduled automation tasks  
- `ft_scraper/utils`: Helper functions  

---

## Installation

1. Clone the repository:

```bash
git clone https://github.com/AhmedTioual/ft_scraper.git
cd ft_scraper

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

playwright install

```

## USAGE


```bash
python -m ft_scraper.scheduler.daily_job
```

## Automation

1. Automate the scraper to run daily.

### Local Cron Job

Open your crontab editor:

```bash
crontab -e

0 0 * * * /home/ahmed/anaconda3/bin/python3 -m ft_scraper.scheduler.daily_job >/dev/null 2>&1
```

2. Automate execution directly in GitHub using a GitHub GitHub Actions

```bash
mkdir -p .github/workflows
touch .github/workflows/ft_daily_job.yml

```
