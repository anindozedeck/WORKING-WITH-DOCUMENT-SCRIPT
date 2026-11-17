# PDF Search Helper

This project is a lightweight PDF reader/search tool that extracts text from a PDF, splits it into readable passages, and highlights the most relevant sections for a question based on keyword overlap.

It is useful for quickly locating the portions of a document that are most likely to answer a search query, with page numbers included for citation.

## How to run

1. Install dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

2. Run the script with a PDF file:

   ```bash
   python Document_Reader_Script.py "path/to/your/file.pdf"
   ```

3. Ask a question in the prompt, for example:

   ```text
   Question: What are the main risks mentioned in the document?
   ```

4. Type `quit` to exit the program.

## Optional argument

You can control how many relevant passages are shown:

```bash
python Document_Reader_Script.py "path/to/your/file.pdf" --top-k 5
```

## Notes

- The script works best with text-based PDFs.
- Scanned PDFs may require OCR before this tool can search them effectively.
