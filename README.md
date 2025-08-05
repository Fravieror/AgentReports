# GPS Realtime Daily Report Automation

This Python script automates the login, navigation, report export, and email delivery process for the [GPS Realtime](https://plataforma.gpsrealtime.co) platform using Selenium WebDriver.

## 📋 Features

- Logs in to the GPS Realtime web platform using environment variables.
- Selects a specific tracking device from a dropdown.
- Exports the summary report as an Excel `.xlsx` file.
- Sends the file via email using Gmail and `yagmail`.
- Cleans up temporary directories after execution.

## 🚀 Requirements

- Python 3.8+
- Google Chrome installed
- A Gmail account with [App Password](https://support.google.com/accounts/answer/185833?hl=en) enabled

## 📦 Dependencies

Install required packages:

```bash
pip install selenium webdriver-manager yagmail
