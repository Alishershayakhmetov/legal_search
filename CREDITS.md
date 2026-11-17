# Credits and third-party works

The project code is released under the MIT licence (see `LICENSE`). Everything below was **used, not written by us**; each keeps its own licence.
Licences were read from the project pages or the Hugging Face / Mendeley APIs on 2026-11-17 unless marked otherwise; check them again before redistributing anything.

## Data

| Work | Authors / owner | Licence | How it is used |
|---|---|---|---|
| [KazakhLawCorpus](https://huggingface.co/datasets/Arailym-tleubayeva/KazakhLawCorpus) (Hugging Face); paper: A. Tleubayeva, A. Mansurova, A. Shomanov, Z. Makhambetova, P. S. Boluk, *KazakhLawCorpus: A Large-Scale Metadata Corpus for Kazakh Legislation*, Data 2026, 11(9), 217, [doi:10.3390/data11090217](https://doi.org/10.3390/data11090217) | Arailym Tleubayeva et al. | Apache-2.0 | metadata of 223,245 legal acts (titles, kinds, bodies, dates, status) |
| [KazakhLawCorpus-clean](https://huggingface.co/datasets/Arailym-tleubayeva/KazakhLawCorpus-clean) | Arailym Tleubayeva | CC BY 4.0 | the variant suggested in the course topic list; we used the main repository and our own audit |
| [Textual Foundations of Justice: Kazakhstani laws and jurisprudence dataset](https://data.mendeley.com/datasets/jdpc5658nh), DOI 10.17632/jdpc5658nh.3 (Mendeley Data, 2024) | Iskander Akhmetov, Alikhan Zhamankhan, Nur Zhetesov, Aruzhan Kubaeva (Kazakh-British Technical University) | CC BY 4.0 | full texts of current Kazakhstani laws as of 01.04.2024 (ru, kk); the data are **not** in this repository |
| [Adilet legal information system](https://adilet.zan.kz) | Ministry of Justice of the Republic of Kazakhstan | official texts | link-out only; nothing was scraped |
| [Hugging Face Hub](https://huggingface.co) | Hugging Face | — | hosting of the datasets and models above |

Our derived files in `release/` (test set, parallel Russian–Kazakh article pairs, glossary) contain or are derived from the CC BY 4.0 texts and must keep the attribution above.

## Models

| Model | Authors | Licence | Use |
|---|---|---|---|
| [BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3) — Chen et al., [arXiv:2402.03216](https://arxiv.org/abs/2402.03216) | BAAI | MIT | best retriever, answer-sentence checks |
| [intfloat/multilingual-e5-small / base / large](https://huggingface.co/intfloat/multilingual-e5-base) — Wang et al., [arXiv:2402.05672](https://arxiv.org/abs/2402.05672) | Microsoft (intfloat) | MIT | comparison retrievers |
| [Qwen/Qwen3-Embedding-0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B) | Alibaba Qwen team | Apache-2.0 | encoder sweep |
| [BAAI/bge-reranker-v2-m3](https://huggingface.co/BAAI/bge-reranker-v2-m3) | BAAI | Apache-2.0 | re-ranking experiment |
| [facebook/nllb-200-distilled-600M](https://huggingface.co/facebook/nllb-200-distilled-600M) — NLLB Team, [arXiv:2207.04672](https://arxiv.org/abs/2207.04672) | Meta AI | **CC BY-NC 4.0 (non-commercial)** | query and snippet translation; do not use this part commercially |
| [Gemma 3 4B](https://ai.google.dev/gemma) via [Ollama](https://ollama.com) — Gemma Team, [arXiv:2503.19786](https://arxiv.org/abs/2503.19786) | Google DeepMind | [Gemma Terms of Use](https://ai.google.dev/gemma/terms) | optional local answer generation |
| [qwen2.5:3b](https://ollama.com/library/qwen2.5) | Alibaba Qwen team | see model page | probed for answers, not used |

## Software

[Python](https://www.python.org) · [PyTorch](https://pytorch.org) (BSD-3) · [sentence-transformers](https://www.sbert.net) (Apache-2.0) · [Transformers](https://github.com/huggingface/transformers) (Apache-2.0) ·
[pandas](https://pandas.pydata.org) (BSD-3) · [NumPy](https://numpy.org) (BSD-3) · [SciPy](https://scipy.org) (BSD-3) · [scikit-learn](https://scikit-learn.org) (BSD-3) · [Apache Arrow / PyArrow](https://arrow.apache.org) (Apache-2.0) ·
[NLTK](https://www.nltk.org) (Apache-2.0; Snowball stemmer) · [matplotlib](https://matplotlib.org) · [SQLite](https://www.sqlite.org) (public domain) · [psutil](https://github.com/giampaolo/psutil) (BSD-3) ·
[python-docx](https://github.com/python-openxml/python-docx) and [python-pptx](https://github.com/scanny/python-pptx) (MIT) · [pytest](https://pytest.org) (MIT) · [sacremoses](https://github.com/hplt-project/sacremoses) (MIT) ·
[SentencePiece](https://github.com/google/sentencepiece) (Apache-2.0) · [LibreOffice](https://www.libreoffice.org) (MPL-2.0, PDF conversion) · [Ollama](https://github.com/ollama/ollama) (MIT).
Exact versions: `requirements.txt`.

## Methods and papers

* BM25: S. Robertson, H. Zaragoza, *The Probabilistic Relevance Framework: BM25 and Beyond*, Foundations and Trends in IR 3(4), 2009.
* Reciprocal rank fusion: G. Cormack, C. Clarke, S. Büttcher, SIGIR 2009.
* nDCG: K. Järvelin, J. Kekäläinen, *Cumulated gain-based evaluation of IR techniques*, ACM TOIS 20(4), 2002.
* Pooling for test collections: K. Sparck Jones, C. J. van Rijsbergen, *Report on the need for and provision of an "ideal" information retrieval test collection*, British Library R&D Report 5266, 1975.
* Bootstrap: B. Efron, R. Tibshirani, *An Introduction to the Bootstrap*, Chapman & Hall, 1993.
* Snowball stemmer: M. Porter, *Snowball: A language for stemming algorithms*, 2001.
* Datasheets for datasets: T. Gebru et al., [arXiv:1803.09010](https://arxiv.org/abs/1803.09010) (format of `release/*/DATASHEET.md`).

## AI assistance

Parts of the code, the drafts of the test questions and relevance judgments, and the text of the report were produced with an AI assistant (Claude, Anthropic) working in this repository, and then reviewed by the team.
