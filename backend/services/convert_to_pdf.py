"""
Markdown을 PDF로 변환하는 스크립트
"""
import markdown
import os

def md_to_html(md_path, html_path):
    """Markdown을 HTML로 변환"""
    with open(md_path, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # Markdown을 HTML로 변환
    html_content = markdown.markdown(
        md_content,
        extensions=['tables', 'fenced_code', 'codehilite']
    )
    
    # CSS 스타일 추가
    full_html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>2026 수능 표준점수 및 백분위 산출 방식</title>
    <style>
        body {{
            font-family: 'Malgun Gothic', '맑은 고딕', 'Apple SD Gothic Neo', sans-serif;
            max-width: 900px;
            margin: 40px auto;
            padding: 20px;
            line-height: 1.8;
            color: #333;
            background-color: #fff;
        }}
        h1 {{
            color: #1a1a1a;
            border-bottom: 3px solid #3b82f6;
            padding-bottom: 10px;
            margin-top: 40px;
        }}
        h2 {{
            color: #2563eb;
            margin-top: 30px;
            border-left: 4px solid #3b82f6;
            padding-left: 12px;
        }}
        h3 {{
            color: #1e40af;
            margin-top: 20px;
        }}
        h4 {{
            color: #1e3a8a;
            margin-top: 15px;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        th {{
            background-color: #3b82f6;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }}
        td {{
            padding: 10px 12px;
            border: 1px solid #e5e7eb;
        }}
        tr:nth-child(even) {{
            background-color: #f9fafb;
        }}
        tr:hover {{
            background-color: #f3f4f6;
        }}
        code {{
            background-color: #f3f4f6;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }}
        pre {{
            background-color: #1f2937;
            color: #f9fafb;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            line-height: 1.5;
        }}
        pre code {{
            background-color: transparent;
            color: #f9fafb;
            padding: 0;
        }}
        hr {{
            border: none;
            border-top: 2px solid #e5e7eb;
            margin: 30px 0;
        }}
        strong {{
            color: #1a1a1a;
            font-weight: 600;
        }}
        blockquote {{
            border-left: 4px solid #d1d5db;
            padding-left: 16px;
            color: #6b7280;
            font-style: italic;
            margin: 20px 0;
        }}
        ul, ol {{
            margin: 15px 0;
            padding-left: 30px;
        }}
        li {{
            margin: 8px 0;
        }}
        .footer {{
            margin-top: 60px;
            padding-top: 20px;
            border-top: 2px solid #e5e7eb;
            text-align: center;
            color: #6b7280;
            font-size: 0.9em;
        }}
        @media print {{
            body {{
                margin: 0;
                padding: 20px;
            }}
            h1 {{
                page-break-before: always;
            }}
            h1:first-of-type {{
                page-break-before: avoid;
            }}
            table {{
                page-break-inside: avoid;
            }}
        }}
    </style>
</head>
<body>
{html_content}
<div class="footer">
    <p>본 문서는 브라우저에서 Ctrl+P (또는 Cmd+P)를 눌러 PDF로 저장할 수 있습니다.</p>
</div>
</body>
</html>"""
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(full_html)
    
    print(f"✅ HTML 파일 생성 완료: {html_path}")
    print(f"   브라우저에서 열어 Ctrl+P (Cmd+P)로 PDF 저장 가능")

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    md_path = os.path.join(script_dir, "docs", "score_calculation_method.md")
    html_path = os.path.join(script_dir, "docs", "score_calculation_method.html")
    
    if os.path.exists(md_path):
        md_to_html(md_path, html_path)
    else:
        print(f"❌ Markdown 파일을 찾을 수 없습니다: {md_path}")
