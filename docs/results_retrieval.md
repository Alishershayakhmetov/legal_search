# Retrieval results (judgments v1)

Provisional: the judgments are an AI-drafted set that the author has not yet reviewed. Round 1 (hand-checked articles) was extended in round 2 by judging the top results of eight system runs: 376 articles are judged in total (67 answer a need, 100 are related, 209 were read and rejected). Judgments are still incomplete, so every number is a lower bound. 45 non-title needs per language; 95% bootstrap intervals on MRR@10 are wide (about ±0.1), so differences of a few points are noise.

## 1. Analyzers and weighting, article passages only (BM25 vs TF-IDF vs keyword overlap)

| lang | analyzer | scheme | Success@5 | Success@10 | Recall@50 | MRR@10 | nDCG@10 |
|---|---|---|---|---|---|---|---|
| ru | word | bm25 | 0.16 | 0.24 | 0.28 | 0.097 | 0.113 |
| ru | word | tfidf | 0.07 | 0.18 | 0.23 | 0.038 | 0.072 |
| ru | word | overlap | 0.11 | 0.22 | 0.23 | 0.070 | 0.076 |
| ru | p5 | bm25 | 0.22 | 0.31 | 0.46 | 0.131 | 0.168 |
| ru | p5 | tfidf | 0.11 | 0.22 | 0.37 | 0.083 | 0.114 |
| ru | p5 | overlap | 0.07 | 0.09 | 0.34 | 0.058 | 0.065 |
| ru | stem | bm25 | 0.33 | 0.42 | 0.52 | 0.184 | 0.204 |
| ru | stem | tfidf | 0.24 | 0.33 | 0.44 | 0.119 | 0.152 |
| ru | stem | overlap | 0.11 | 0.16 | 0.32 | 0.070 | 0.072 |
| kk | word | bm25 | 0.22 | 0.31 | 0.36 | 0.125 | 0.136 |
| kk | word | tfidf | 0.18 | 0.22 | 0.29 | 0.097 | 0.112 |
| kk | word | overlap | 0.11 | 0.13 | 0.27 | 0.045 | 0.060 |
| kk | p5 | bm25 | 0.22 | 0.31 | 0.39 | 0.187 | 0.173 |
| kk | p5 | tfidf | 0.16 | 0.20 | 0.28 | 0.081 | 0.110 |
| kk | p5 | overlap | 0.13 | 0.18 | 0.23 | 0.044 | 0.067 |
| kk | stem | bm25 | 0.20 | 0.31 | 0.41 | 0.122 | 0.137 |
| kk | stem | tfidf | 0.16 | 0.20 | 0.32 | 0.086 | 0.107 |
| kk | stem | overlap | 0.11 | 0.13 | 0.22 | 0.051 | 0.064 |

word = word forms, p5 = first five characters, stem = Snowball (ru) or suffix stripping (kk).

## 2. Systems compared on article passages (230,545 passages, ru and kk)

| lang | system | Success@5 | Success@10 | Recall@50 | MRR@10 | nDCG@10 |
|---|---|---|---|---|---|---|
| ru | BM25 (stem) | 0.33 | 0.42 | 0.52 | 0.184 | 0.204 |
| ru | bge-m3 dense | 0.71 | 0.80 | 0.89 | 0.407 | 0.451 |
| ru | bge-m3 hybrid | 0.51 | 0.60 | 0.85 | 0.320 | 0.348 |
| ru | multilingual-e5-base dense | 0.53 | 0.67 | 0.85 | 0.324 | 0.390 |
| ru | multilingual-e5-base hybrid | 0.47 | 0.58 | 0.79 | 0.281 | 0.326 |
| ru | multilingual-e5-small dense | 0.44 | 0.58 | 0.74 | 0.279 | 0.351 |
| ru | multilingual-e5-small hybrid | 0.44 | 0.49 | 0.72 | 0.254 | 0.302 |
| kk | BM25 (p5) | 0.22 | 0.31 | 0.39 | 0.187 | 0.173 |
| kk | bge-m3 dense | 0.56 | 0.73 | 0.85 | 0.365 | 0.398 |
| kk | bge-m3 hybrid | 0.33 | 0.53 | 0.77 | 0.242 | 0.261 |
| kk | multilingual-e5-base dense | 0.31 | 0.36 | 0.54 | 0.167 | 0.184 |
| kk | multilingual-e5-base hybrid | 0.29 | 0.44 | 0.52 | 0.186 | 0.210 |
| kk | multilingual-e5-small dense | 0.38 | 0.49 | 0.58 | 0.203 | 0.213 |
| kk | multilingual-e5-small hybrid | 0.36 | 0.47 | 0.57 | 0.233 | 0.236 |

## 3. Effect of the corpus: article passages vs all prose passages (BM25)

| lang | analyzer | docs (articles) | S@10 | MRR | docs (all prose) | S@10 | MRR |
|---|---|---|---|---|---|---|---|
| kk | p5 | 111,820 | 0.31 | 0.187 | 824,247 | 0.24 | 0.125 |
| ru | stem | 118,725 | 0.42 | 0.184 | 874,823 | 0.18 | 0.081 |

Same comparison for dense retrieval (e5-small, 230,545 article passages vs 1,699,070 prose passages):

| lang | system | S@10 (articles) | MRR (articles) | S@10 (all prose) | MRR (all prose) |
|---|---|---|---|---|---|
| ru | multilingual-e5-small dense | 0.58 | 0.279 | 0.44 | 0.208 |
| kk | multilingual-e5-small dense | 0.49 | 0.203 | 0.36 | 0.146 |

Every system loses quality when non-article prose (orders, regional decisions) is added; the ranking of the systems stays the same. Part of the loss is incomplete judgments: some of those passages may be relevant.

## 4. English queries (no English text exists in the corpus)

direct = the English query against Russian and Kazakh passages with a multilingual model; translated = NLLB-600M translation of the query into Russian and Kazakh first.

| model | system | Success@5 | Success@10 | Recall@50 | MRR@10 | nDCG@10 |
|---|---|---|---|---|---|---|
| bge-m3 | dense_cross | 0.60 | 0.71 | 0.84 | 0.373 | 0.391 |
| bge-m3 | bm25_translated | 0.22 | 0.29 | 0.44 | 0.144 | 0.149 |
| bge-m3 | dense_translated | 0.53 | 0.64 | 0.85 | 0.338 | 0.348 |
| bge-m3 | hybrid_translated | 0.51 | 0.71 | 0.83 | 0.330 | 0.356 |
| multilingual-e5-base | dense_cross | 0.11 | 0.13 | 0.31 | 0.086 | 0.096 |
| multilingual-e5-base | bm25_translated | 0.22 | 0.29 | 0.44 | 0.144 | 0.149 |
| multilingual-e5-base | dense_translated | 0.31 | 0.36 | 0.63 | 0.197 | 0.218 |
| multilingual-e5-base | hybrid_translated | 0.33 | 0.40 | 0.60 | 0.197 | 0.233 |
| multilingual-e5-small | dense_cross | 0.18 | 0.24 | 0.32 | 0.090 | 0.101 |
| multilingual-e5-small | bm25_translated | 0.22 | 0.29 | 0.44 | 0.144 | 0.149 |
| multilingual-e5-small | dense_translated | 0.31 | 0.44 | 0.64 | 0.140 | 0.217 |
| multilingual-e5-small | hybrid_translated | 0.42 | 0.53 | 0.63 | 0.272 | 0.284 |

## 5. Title layer (find an act by name), 8 needs per language, 439,124 titles

Eight queries per language: one query is 0.125, so these rows only indicate a direction.

| lang | system | Success@1 | Success@5 | Success@10 | MRR@10 |
|---|---|---|---|---|---|

## 6. What the second round of judgments changed (article passages)

| lang | system | S@10 v0 | S@10 v1 | MRR v0 | MRR v1 |
|---|---|---|---|---|---|
| ru | BM25 (stem) | 0.38 | 0.42 | 0.139 | 0.184 |
| ru | multilingual-e5-small dense | 0.53 | 0.58 | 0.210 | 0.279 |
| ru | multilingual-e5-base dense | 0.62 | 0.67 | 0.278 | 0.324 |
| ru | bge-m3 dense | 0.78 | 0.80 | 0.339 | 0.407 |
| kk | BM25 (p5) | 0.29 | 0.31 | 0.165 | 0.187 |
| kk | multilingual-e5-small dense | 0.47 | 0.49 | 0.169 | 0.203 |
| kk | multilingual-e5-base dense | 0.31 | 0.36 | 0.132 | 0.167 |
| kk | bge-m3 dense | 0.69 | 0.73 | 0.316 | 0.365 |

Adding judgments raises every system a little and keeps the order of systems, so the first set was incomplete but not misleading. The pool came from the same systems that are being compared (and from BM25), which favours them slightly against a method that was not in the pool.

## 7. Cost of the dense models (RTX 3050 Laptop 4 GB, fp16, 384 tokens)

| model | params | dim | passages/s | hours for 1.70M passages | GPU memory |
|---|---|---|---|---|---|
| multilingual-e5-small | 118M | 384 | 377 | 1.3 | 0.4 GB |
| multilingual-e5-base | 278M | 768 | 161 | 2.9 | 0.8 GB |
| bge-m3 | 568M | 1024 | 53 | 8.9 | 1.5 GB |

Median passage length is 289 tokens; 8% exceed 384 and are truncated.
