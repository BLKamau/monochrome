#!/usr/bin/env python
"""
Export API documentation to various formats.
"""

import os
import sys
import json
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'monochrome_backend.settings')
import django
django.setup()

from django.urls import reverse
from django.test import RequestFactory
from rest_framework.request import Request


def export_openapi_schema():
    """Export OpenAPI schema to JSON file."""
    print("Exporting OpenAPI schema...")
    
    # Import schema view
    from monochrome_backend.urls import schema_view
    
    # Create a fake request
    factory = RequestFactory()
    request = factory.get('/api/schema/')
    
    # Get schema
    schema = schema_view.without_ui(cache_timeout=0)(request)
    
    # Save to file
    output_dir = Path(__file__).parent.parent / 'docs'
    output_dir.mkdir(exist_ok=True)
    
    schema_file = output_dir / 'openapi_schema.json'
    with open(schema_file, 'w') as f:
        json.dump(schema.data, f, indent=2)
    
    print(f"✓ Schema exported to {schema_file}")
    
    # Generate Markdown documentation
    generate_markdown_docs(schema.data, output_dir)


def generate_markdown_docs(schema, output_dir):
    """Generate Markdown documentation from OpenAPI schema."""
    print("Generating Markdown documentation...")
    
    md_content = f"""# Monochrome API Documentation

{schema.get('info', {}).get('description', '')}

**Version:** {schema.get('info', {}).get('version', '1.0.0')}

## Base URL

```
{schema.get('servers', [{'url': 'http://localhost:8000'}])[0]['url']}
```

## Authentication

This API uses JWT Bearer token authentication. Include the token in the Authorization header:

```
Authorization: Bearer <your-token>
```

## Endpoints

"""
    
    # Group endpoints by tag
    paths = schema.get('paths', {})
    endpoints_by_tag = {}
    
    for path, methods in paths.items():
        for method, details in methods.items():
            if method in ['get', 'post', 'put', 'patch', 'delete']:
                tags = details.get('tags', ['Other'])
                for tag in tags:
                    if tag not in endpoints_by_tag:
                        endpoints_by_tag[tag] = []
                    endpoints_by_tag[tag].append({
                        'path': path,
                        'method': method.upper(),
                        'summary': details.get('summary', ''),
                        'description': details.get('description', ''),
                        'parameters': details.get('parameters', []),
                        'requestBody': details.get('requestBody', {}),
                        'responses': details.get('responses', {})
                    })
    
    # Write endpoints by tag
    for tag, endpoints in endpoints_by_tag.items():
        md_content += f"\n### {tag}\n\n"
        
        for endpoint in endpoints:
            md_content += f"#### {endpoint['method']} {endpoint['path']}\n\n"
            if endpoint['summary']:
                md_content += f"{endpoint['summary']}\n\n"
            if endpoint['description']:
                md_content += f"{endpoint['description']}\n\n"
            
            # Parameters
            if endpoint['parameters']:
                md_content += "**Parameters:**\n\n"
                for param in endpoint['parameters']:
                    required = '(required)' if param.get('required') else '(optional)'
                    md_content += f"- `{param['name']}` {required} - {param.get('description', '')}\n"
                md_content += "\n"
            
            # Request body
            if endpoint['requestBody']:
                md_content += "**Request Body:**\n\n```json\n"
                # Extract schema example
                content = endpoint['requestBody'].get('content', {})
                if 'application/json' in content:
                    schema_ref = content['application/json'].get('schema', {})
                    md_content += json.dumps({"example": "request body"}, indent=2)
                md_content += "\n```\n\n"
            
            # Responses
            if endpoint['responses']:
                md_content += "**Responses:**\n\n"
                for status_code, response in endpoint['responses'].items():
                    md_content += f"- `{status_code}`: {response.get('description', '')}\n"
                md_content += "\n"
    
    # Save Markdown file
    md_file = output_dir / 'API_Reference.md'
    with open(md_file, 'w') as f:
        f.write(md_content)
    
    print(f"✓ Markdown documentation exported to {md_file}")


def main():
    print("=== Monochrome API Documentation Export ===\n")
    export_openapi_schema()
    print("\n✓ Documentation export completed!")


if __name__ == "__main__":
    main()

