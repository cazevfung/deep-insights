# 你的任务

分析评论并提取关键信息，以**标记列表**的形式用于检索。**严格按照系统提示中的标记区分标准进行分类。**

## 评论内容
{comments_content}

## 输出要求
- 仅输出 JSON 格式
- `key_facts_from_comments` / `key_opinions_from_comments` / `key_datapoints_from_comments` 各 5-15 条，`major_themes` 3-10 条，`top_engagement_markers` 3-8 条
- 每个标记 10-50 字，聚焦高互动评论，避免重复描述

## 参考输出格式（必须是有效的JSON）
```json
{
  "total_comments": 1000,
  "key_facts_from_comments": ["...", ...],
  "key_opinions_from_comments": ["...", ...],
  "key_datapoints_from_comments": ["...", ...],
  "major_themes": ["...", ...],
  "sentiment_overview": "mostly_positive|mixed|mostly_negative",
  "top_engagement_markers": ["...", ...],
  "total_markers": 25
}
```
