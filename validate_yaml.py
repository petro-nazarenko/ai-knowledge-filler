#!/usr/bin/env python3
"""
YAML Metadata Validator for AI Knowledge Filler
Single source of truth for all validation logic.
"""

import yaml
import glob
import sys
from datetime import datetime
from pathlib import Path

# Valid enum values
VALID_TYPES = ['concept', 'guide', 'reference', 'checklist', 'project', 'roadmap', 'template', 'audit']
VALID_LEVELS = ['beginner', 'intermediate', 'advanced']
VALID_STATUSES = ['draft', 'active', 'completed', 'archived']

VALID_DOMAINS = [
    'ai-system', 'system-design', 'api-design', 'data-engineering',
    'security', 'devops', 'product-management', 'consulting',
    'workflow-automation', 'prompt-engineering', 'business-strategy',
    'project-management', 'knowledge-management', 'documentation',
    'learning-systems', 'frontend-engineering', 'backend-engineering',
    'infrastructure', 'machine-learning', 'data-science', 'operations',
    'finance', 'marketing', 'sales', 'healthcare', 'finance-tech',
    'education-tech', 'e-commerce'
]

# FILES TO EXCLUDE (Single Source of Truth)
EXCLUDED_FILES = {
    'README.md',
    'CONTRIBUTING.md',
    'DEPLOYMENT_READY.md',
    'LICENSE.md',
    'CHANGELOG.md',
    'CLAUDE.md'
}

EXCLUDED_DIRS = {
    '.github',
    'node_modules',
    '.git',
    '__pycache__',
    'venv',
    '.venv'
}

def should_validate_file(filepath):
    """
    Determine if a file should be validated.
    Single source of truth for exclusion logic.
    """
    path = Path(filepath)
    
    # Check if in excluded directory
    for excluded_dir in EXCLUDED_DIRS:
        if excluded_dir in path.parts:
            return False
    
    # Check if excluded filename
    if path.name in EXCLUDED_FILES:
        return False
    
    # Must be markdown
    if path.suffix != '.md':
        return False
    
    return True

def validate_date_format(date_str):
    """Validate ISO 8601 date format (YYYY-MM-DD)"""
    try:
        datetime.strptime(str(date_str), '%Y-%m-%d')
        return True
    except ValueError:
        return False

def validate_file(filepath):
    """Validate single Markdown file"""
    errors = []
    warnings = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for YAML frontmatter
    if not content.startswith('---'):
        return ['No YAML frontmatter found'], []
    
    try:
        # Extract and parse YAML
        parts = content.split('---')
        if len(parts) < 3:
            return ['Invalid YAML frontmatter structure'], []
        
        yaml_content = parts[1]
        metadata = yaml.safe_load(yaml_content)
        
        if not metadata:
            return ['Empty YAML frontmatter'], []
        
        # Required fields
        required_fields = ['title', 'type', 'domain', 'level', 'status', 'created', 'updated']
        for field in required_fields:
            if field not in metadata:
                errors.append(f"Missing required field: {field}")
        
        # Validate type
        if 'type' in metadata and metadata['type'] not in VALID_TYPES:
            errors.append(f"Invalid type: {metadata['type']}. Must be one of: {', '.join(VALID_TYPES)}")
        
        # Validate level
        if 'level' in metadata and metadata['level'] not in VALID_LEVELS:
            errors.append(f"Invalid level: {metadata['level']}. Must be one of: {', '.join(VALID_LEVELS)}")
        
        # Validate status
        if 'status' in metadata and metadata['status'] not in VALID_STATUSES:
            errors.append(f"Invalid status: {metadata['status']}. Must be one of: {', '.join(VALID_STATUSES)}")
        
        # Validate domain
        if 'domain' in metadata and metadata['domain'] not in VALID_DOMAINS:
            warnings.append(f"Domain '{metadata['domain']}' not in standard taxonomy")
        
        # Validate dates
        if 'created' in metadata and not validate_date_format(metadata['created']):
            errors.append(f"Invalid created date format: {metadata['created']}. Use YYYY-MM-DD")
        
        if 'updated' in metadata and not validate_date_format(metadata['updated']):
            errors.append(f"Invalid updated date format: {metadata['updated']}. Use YYYY-MM-DD")
        
        # Validate tags is array
        if 'tags' in metadata and not isinstance(metadata['tags'], list):
            errors.append("Tags must be an array")
        
        # Validate related is array (if present)
        if 'related' in metadata and metadata['related'] is not None:
            if not isinstance(metadata['related'], list):
                errors.append("Related must be an array or null")
        
        # Warnings for best practices
        if 'tags' in metadata and isinstance(metadata['tags'], list) and len(metadata['tags']) < 3:
            warnings.append("Fewer than 3 tags (recommended: 3-10)")
        
        if 'related' not in metadata or not metadata['related']:
            warnings.append("No related links (recommended for knowledge graph)")
        
    except yaml.YAMLError as e:
        errors.append(f"YAML parsing error: {str(e)}")
    except Exception as e:
        errors.append(f"Unexpected error: {str(e)}")
    
    return errors, warnings

def main():
    """Validate all Markdown files in repository"""
    print("🔍 AI Knowledge Filler - YAML Metadata Validator\n")
    
    # Find all markdown files
    all_files = glob.glob('**/*.md', recursive=True)
    
    # Filter using centralized logic
    md_files = [f for f in all_files if should_validate_file(f)]
    
    print(f"📁 Found {len(all_files)} total .md files")
    print(f"✅ Validating {len(md_files)} knowledge files")
    print(f"⏭️  Skipping {len(all_files) - len(md_files)} documentation files\n")
    
    total_files = len(md_files)
    valid_files = 0
    files_with_errors = 0
    files_with_warnings = 0
    
    for filepath in sorted(md_files):
        errors, warnings = validate_file(filepath)
        
        if errors:
            files_with_errors += 1
            print(f"❌ {filepath}")
            for error in errors:
                print(f"   ERROR: {error}")
        elif warnings:
            files_with_warnings += 1
            print(f"⚠️  {filepath}")
            for warning in warnings:
                print(f"   WARNING: {warning}")
        else:
            valid_files += 1
            print(f"✅ {filepath}")
    
    print(f"\n📊 Validation Summary:")
    print(f"   Total files validated: {total_files}")
    print(f"   ✅ Valid: {valid_files}")
    print(f"   ⚠️  Warnings: {files_with_warnings}")
    print(f"   ❌ Errors: {files_with_errors}")
    
    if files_with_errors > 0:
        print(f"\n❌ Validation failed: {files_with_errors} file(s) with errors")
        sys.exit(1)
    else:
        print(f"\n✅ All files valid!")
        sys.exit(0)

if __name__ == '__main__':
    main()
