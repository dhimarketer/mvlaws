# MV Laws - Maldives Legal Database

A comprehensive legal database and search system for Maldivian laws and regulations.

## Features

- **Legal Document Search**: Full-text search across Maldivian legal documents
- **Bilingual Support**: Documents available in both English and Dhivehi
- **Web Interface**: User-friendly web application built with Flask
- **Database Management**: SQLite-based storage with efficient indexing

## Project Structure

```
mvlaws/
├── app.py              # Main Flask application
├── laws/               # Legal documents (English and Dhivehi)
├── templates/          # HTML templates
├── static/             # CSS and static assets
├── backup/             # Backup and migration scripts
└── venv/               # Python virtual environment
```

## Setup

1. **Clone the repository**
   ```bash
   git clone <your-github-repo-url>
   cd mvlaws
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install flask
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Access the application**
   Open your browser and navigate to `http://localhost:5000`

## Usage

- **Search Laws**: Use the search bar to find specific legal documents
- **Browse Categories**: Navigate through different legal categories
- **View Documents**: Read full legal texts with proper formatting

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is for educational and research purposes. Please ensure compliance with local laws and regulations when using legal documents.

## Contact

For questions or contributions, please open an issue on GitHub.
