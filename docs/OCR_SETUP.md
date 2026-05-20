# OCR Setup

The backend now accepts image uploads through `POST /api/analyze/file`.

Supported file types:

- `application/pdf`
- `image/png`
- `image/jpeg`
- `image/webp`
- `image/bmp`
- `image/tiff`

## Local Requirement

The Python dependency `pytesseract` is installed through `requirements.txt`, but it is only a wrapper.
Windows also needs the Tesseract OCR program and Korean language data.

After installing Tesseract OCR, set this in `.env`:

```env
TESSERACT_CMD=C:/Program Files/Tesseract-OCR/tesseract.exe
TESSDATA_DIR=ocr/tessdata
OCR_LANGUAGE=kor+eng
OCR_PSM=6
OCR_MIN_TEXT_LENGTH=20
OCR_PDF_MAX_PAGES=20
OCR_PDF_DPI=200
```

If Korean OCR data is missing, use `OCR_LANGUAGE=eng` temporarily or install `kor.traineddata`.
When Windows blocks writes to `C:/Program Files/Tesseract-OCR/tessdata`, place `eng.traineddata`,
`osd.traineddata`, `kor.traineddata`, and any sub-language data requested by Tesseract in
`ocr/tessdata` and keep `TESSDATA_DIR=ocr/tessdata`.

For the current official `kor.traineddata`, Tesseract may also request `chi_tra.traineddata`.

## PDF OCR Behavior

Text-based PDFs are handled first with PyMuPDF text extraction. If a PDF has no extractable text,
the backend renders up to `OCR_PDF_MAX_PAGES` pages as images and runs Tesseract OCR on those pages.
Increase `OCR_PDF_MAX_PAGES` only when long scanned PDFs are expected, because each page adds OCR time.

OCR output is rejected when it is too short or mostly numeric/symbol noise. If Korean OCR returns
garbled digits, verify that `kor.traineddata` and any requested helper data such as
`chi_tra.traineddata` exist under `TESSDATA_DIR`, then test with real screenshots or scanned PDFs.

## Frontend Upload Shape

Use `multipart/form-data`:

- `file`: PNG/JPG screenshot or PDF
- `session_key`: optional
- `service_name`: optional

Example:

```bash
curl -X POST "http://127.0.0.1:8000/api/analyze/file" \
  -F "file=@terms.png" \
  -F "session_key=test-session" \
  -F "service_name=서비스명"
```

The response returns `job_id`. Fetch the analysis with:

```bash
curl "http://127.0.0.1:8000/api/result/{job_id}"
```
