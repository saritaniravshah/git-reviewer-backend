FILE_STRUCTURE_PROMPT = """Analyze the following repository file structure and provide feedback in JSON format:

File Structure:
{file_tree}

Return your analysis in this exact JSON format:
{{
  "overall_rating": "good|needs_improvement|poor",
  "issues": [
    {{
      "type": "structure|organization|naming",
      "severity": "info|warning|critical",
      "message": "Description of the issue",
      "suggestion": "How to improve"
    }}
  ],
  "strengths": ["List of good practices found"],
  "recommendations": ["List of improvement suggestions"]
}}"""

FILE_REVIEW_PROMPT = """Review the following code file and identify issues in JSON format:

File: {filename}
Content:
{content}

Analyze for:
1. Code quality and best practices
2. Grammar and naming conventions
3. Security vulnerabilities (API keys, secrets, etc.)
4. Potential bugs
5. Performance issues

Return your review in this exact JSON format:
{{
  "filename": "{filename}",
  "issues": [
    {{
      "line": 10,
      "type": "security|bug|grammar|style|performance",
      "severity": "info|warning|critical",
      "message": "Description of the issue",
      "suggestion": "How to fix it"
    }}
  ],
  "summary": {{
    "total_issues": 0,
    "critical": 0,
    "warnings": 0,
    "info": 0
  }}
}}"""
