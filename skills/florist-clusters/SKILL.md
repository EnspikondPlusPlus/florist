---
name: florist-clusters
description: "Compost clusters: give each automatically formed cluster of compost items a short theme label. Returns ClusterLabels."
step: clusters
output: ClusterLabels
---

# Cluster labels

Florist grouped compost items by text similarity. For each cluster id in the context (with its
items' titles and top terms), return a theme label of 2–4 words that a person would recognise as
"one of my recurring interests" (e.g. "on-device LLM inference", "robot learning from video").
Return `labels` as `{cluster_id: label}` for every cluster.
