# Retrieval results (judgments v1)

Provisional: the judgments are an AI-drafted set that the author has not yet reviewed. Round 1 (hand-checked articles) was extended in round 2 by judging the top results of eight system runs: 376 articles are judged in total (67 answer a need, 100 are related, 209 were read and rejected). Judgments are still incomplete, so every number is a lower bound. 45 non-title needs per language; 95% bootstrap intervals on MRR@10 are wide (about ±0.1), so differences of a few points are noise.

## 1. Analyzers and weighting, article passages only (BM25 vs TF-IDF vs keyword overlap)

| lang | analyzer | scheme | Success@5 | Success@10 | Recall@50 | MRR@10 | nDCG@10 |
|---|---|---|---|---|---|---|---|
| ru | word | bm25 | 0.16 | 0.20 | 0.28 | 0.092 | 0.105 |
| ru | word | tfidf | 0.04 | 0.16 | 0.23 | 0.032 | 0.064 |
| ru | word | overlap | 0.09 | 0.18 | 0.23 | 0.061 | 0.065 |
| ru | p5 | bm25 | 0.20 | 0.29 | 0.46 | 0.109 | 0.149 |
| ru | p5 | tfidf | 0.09 | 0.20 | 0.37 | 0.062 | 0.102 |
| ru | p5 | overlap | 0.07 | 0.07 | 0.29 | 0.039 | 0.043 |
| ru | stem | bm25 | 0.29 | 0.42 | 0.52 | 0.153 | 0.189 |
| ru | stem | tfidf | 0.22 | 0.33 | 0.41 | 0.097 | 0.134 |
| ru | stem | overlap | 0.07 | 0.16 | 0.27 | 0.063 | 0.066 |
| kk | word | bm25 | 0.22 | 0.29 | 0.36 | 0.132 | 0.130 |
| kk | word | tfidf | 0.16 | 0.22 | 0.27 | 0.096 | 0.110 |
| kk | word | overlap | 0.11 | 0.13 | 0.23 | 0.044 | 0.056 |
| kk | p5 | bm25 | 0.22 | 0.31 | 0.39 | 0.166 | 0.167 |
| kk | p5 | tfidf | 0.13 | 0.16 | 0.28 | 0.075 | 0.101 |
| kk | p5 | overlap | 0.09 | 0.18 | 0.23 | 0.035 | 0.062 |
| kk | stem | bm25 | 0.18 | 0.27 | 0.39 | 0.118 | 0.127 |
| kk | stem | tfidf | 0.13 | 0.20 | 0.30 | 0.078 | 0.099 |
| kk | stem | overlap | 0.11 | 0.13 | 0.20 | 0.051 | 0.059 |

word = word forms, p5 = first five characters, stem = Snowball (ru) or suffix stripping (kk).

## 2. Systems compared on article passages (230,545 passages, ru and kk)

| lang | system | Success@5 | Success@10 | Recall@50 | MRR@10 | nDCG@10 |
|---|---|---|---|---|---|---|
| ru | BM25 (stem) | 0.29 | 0.42 | 0.52 | 0.153 | 0.189 |
| ru | bge-m3 dense | 0.67 | 0.80 | 0.89 | 0.383 | 0.425 |
| ru | bge-m3 hybrid | 0.47 | 0.60 | 0.85 | 0.315 | 0.334 |
| ru | multilingual-e5-base dense | 0.51 | 0.67 | 0.81 | 0.295 | 0.362 |
| ru | multilingual-e5-base hybrid | 0.42 | 0.60 | 0.79 | 0.265 | 0.315 |
| ru | multilingual-e5-small dense | 0.42 | 0.53 | 0.72 | 0.259 | 0.327 |
| ru | multilingual-e5-small hybrid | 0.44 | 0.47 | 0.72 | 0.244 | 0.284 |
| kk | BM25 (p5) | 0.22 | 0.31 | 0.39 | 0.166 | 0.167 |
| kk | bge-m3 dense | 0.56 | 0.73 | 0.85 | 0.354 | 0.384 |
| kk | bge-m3 hybrid | 0.29 | 0.53 | 0.78 | 0.240 | 0.258 |
| kk | multilingual-e5-base dense | 0.29 | 0.36 | 0.52 | 0.165 | 0.183 |
| kk | multilingual-e5-base hybrid | 0.24 | 0.40 | 0.52 | 0.168 | 0.194 |
| kk | multilingual-e5-small dense | 0.38 | 0.49 | 0.58 | 0.203 | 0.213 |
| kk | multilingual-e5-small hybrid | 0.33 | 0.44 | 0.57 | 0.201 | 0.217 |

## 3. Effect of the corpus: article passages vs all prose passages (BM25)

| lang | analyzer | docs (articles) | S@10 | MRR | docs (all prose) | S@10 | MRR |
|---|---|---|---|---|---|---|---|
| kk | p5 | 158,415 | 0.31 | 0.166 | 840,322 | 0.24 | 0.115 |
| ru | stem | 160,962 | 0.42 | 0.153 | 888,356 | 0.18 | 0.080 |

Same comparison for dense retrieval (e5-small, 230,545 article passages vs 1,699,070 prose passages):

| lang | system | S@10 (articles) | MRR (articles) | S@10 (all prose) | MRR (all prose) |
|---|---|---|---|---|---|
| ru | multilingual-e5-small dense | 0.53 | 0.259 | 0.44 | 0.209 |
| kk | multilingual-e5-small dense | 0.49 | 0.203 | 0.36 | 0.146 |

Every system loses quality when non-article prose (orders, regional decisions) is added; the ranking of the systems stays the same. Part of the loss is incomplete judgments: some of those passages may be relevant.

## 4. English queries (no English text exists in the corpus)

direct = the English query against Russian and Kazakh passages with a multilingual model; translated = NLLB-600M translation of the query into Russian and Kazakh first.

| model | system | Success@5 | Success@10 | Recall@50 | MRR@10 | nDCG@10 |
|---|---|---|---|---|---|---|
| bge-m3 | dense_cross | 0.56 | 0.69 | 0.83 | 0.321 | 0.356 |
| bge-m3 | bm25_translated | 0.20 | 0.24 | 0.43 | 0.152 | 0.154 |
| bge-m3 | dense_translated | 0.44 | 0.64 | 0.84 | 0.288 | 0.316 |
| bge-m3 | hybrid_translated | 0.51 | 0.67 | 0.83 | 0.305 | 0.331 |
| multilingual-e5-base | dense_cross | 0.11 | 0.13 | 0.29 | 0.086 | 0.092 |
| multilingual-e5-base | bm25_translated | 0.20 | 0.24 | 0.43 | 0.152 | 0.154 |
| multilingual-e5-base | dense_translated | 0.27 | 0.36 | 0.63 | 0.168 | 0.187 |
| multilingual-e5-base | hybrid_translated | 0.36 | 0.38 | 0.58 | 0.175 | 0.203 |
| multilingual-e5-small | dense_cross | 0.16 | 0.22 | 0.32 | 0.082 | 0.094 |
| multilingual-e5-small | bm25_translated | 0.20 | 0.24 | 0.43 | 0.152 | 0.154 |
| multilingual-e5-small | dense_translated | 0.31 | 0.42 | 0.63 | 0.135 | 0.205 |
| multilingual-e5-small | hybrid_translated | 0.42 | 0.51 | 0.64 | 0.252 | 0.272 |

## 5. Title layer (find an act by name), 8 needs per language, 439,124 titles

Eight queries per language: one query is 0.125, so these rows only indicate a direction.

| lang | system | Success@1 | Success@5 | Success@10 | MRR@10 |
|---|---|---|---|---|---|

## 6. What the second round of judgments changed (article passages)

| lang | system | S@10 v0 | S@10 v1 | MRR v0 | MRR v1 |
|---|---|---|---|---|---|
| ru | BM25 (stem) | 0.38 | 0.42 | 0.139 | 0.153 |
| ru | multilingual-e5-small dense | 0.53 | 0.53 | 0.210 | 0.259 |
| ru | multilingual-e5-base dense | 0.62 | 0.67 | 0.278 | 0.295 |
| ru | bge-m3 dense | 0.78 | 0.80 | 0.339 | 0.383 |
| kk | BM25 (p5) | 0.29 | 0.31 | 0.165 | 0.166 |
| kk | multilingual-e5-small dense | 0.47 | 0.49 | 0.169 | 0.203 |
| kk | multilingual-e5-base dense | 0.31 | 0.36 | 0.132 | 0.165 |
| kk | bge-m3 dense | 0.69 | 0.73 | 0.316 | 0.354 |

Adding judgments raises every system a little and keeps the order of systems, so the first set was incomplete but not misleading. The pool came from the same systems that are being compared (and from BM25), which favours them slightly against a method that was not in the pool.

## 7. Cost of the dense models (RTX 3050 Laptop 4 GB, fp16, 384 tokens)

| model | params | dim | passages/s | hours for 1.70M passages | GPU memory |
|---|---|---|---|---|---|
| multilingual-e5-small | 118M | 384 | 377 | 1.3 | 0.4 GB |
| multilingual-e5-base | 278M | 768 | 161 | 2.9 | 0.8 GB |
| bge-m3 | 568M | 1024 | 53 | 8.9 | 1.5 GB |

Median passage length is 289 tokens; 8% exceed 384 and are truncated.
