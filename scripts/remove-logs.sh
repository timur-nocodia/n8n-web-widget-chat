#!/bin/bash

# Script to remove all logging statements from the codebase
# Usage: ./scripts/remove-logs.sh [--dry-run]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

DRY_RUN=false
if [[ "$1" == "--dry-run" ]]; then
    DRY_RUN=true
    echo -e "${YELLOW}DRY RUN MODE - No files will be modified${NC}"
fi

echo -e "${GREEN}Starting log removal process...${NC}"

# Function to count occurrences
count_logs() {
    local pattern="$1"
    local file_type="$2"
    local count=$(rg "$pattern" --type "$file_type" . 2>/dev/null | wc -l || echo "0")
    echo "$count"
}

# Remove JavaScript/TypeScript console statements
remove_js_logs() {
    echo -e "\n${YELLOW}Removing JavaScript/TypeScript console statements...${NC}"
    
    # Patterns to remove (each on its own line for clarity)
    local patterns=(
        # Console methods with optional whitespace
        "^\s*console\.(log|error|warn|info|debug|trace|dir|time|timeEnd|assert|table|group|groupEnd)\(.*\);?\s*$"
        # Multi-line console statements
        "^\s*console\.(log|error|warn|info|debug|trace|dir|time|timeEnd|assert|table|group|groupEnd)\([^)]*$"
    )
    
    # Find all JS/TS files
    local files=$(find . -type f \( -name "*.js" -o -name "*.ts" -o -name "*.jsx" -o -name "*.tsx" -o -name "*.mjs" \) \
                  -not -path "*/node_modules/*" \
                  -not -path "*/.next/*" \
                  -not -path "*/dist/*" \
                  -not -path "*/build/*" \
                  -not -name "*.min.js")
    
    local count=0
    for file in $files; do
        if [[ -f "$file" ]]; then
            # Count console statements in this file
            local file_count=$(grep -E "console\.(log|error|warn|info|debug|trace|dir|time|timeEnd|assert|table|group|groupEnd)" "$file" 2>/dev/null | wc -l || echo "0")
            
            if [[ $file_count -gt 0 ]]; then
                echo "  Processing: $file (found $file_count console statements)"
                
                if [[ "$DRY_RUN" == false ]]; then
                    # Remove single-line console statements
                    sed -i.bak -E '/^\s*console\.(log|error|warn|info|debug|trace|dir|time|timeEnd|assert|table|group|groupEnd)\(.*\);?\s*$/d' "$file"
                    
                    # Remove multi-line console statements (basic approach)
                    # This handles console.log that spans multiple lines
                    perl -i.bak2 -0pe 's/\s*console\.(log|error|warn|info|debug|trace|dir|time|timeEnd|assert|table|group|groupEnd)\([^)]*\);?\s*\n?//gms' "$file"
                    
                    # Clean up backup files
                    rm -f "${file}.bak" "${file}.bak2"
                fi
                
                count=$((count + file_count))
            fi
        fi
    done
    
    echo -e "  ${GREEN}Removed $count console statements${NC}"
}

# Remove HTML inline console statements
remove_html_logs() {
    echo -e "\n${YELLOW}Removing HTML inline console statements...${NC}"
    
    local files=$(find . -type f -name "*.html" \
                  -not -path "*/node_modules/*" \
                  -not -path "*/dist/*" \
                  -not -path "*/build/*")
    
    local count=0
    for file in $files; do
        if [[ -f "$file" ]]; then
            local file_count=$(grep -E "console\.(log|error|warn|info|debug)" "$file" 2>/dev/null | wc -l || echo "0")
            
            if [[ $file_count -gt 0 ]]; then
                echo "  Processing: $file (found $file_count console statements)"
                
                if [[ "$DRY_RUN" == false ]]; then
                    # Remove console statements within script tags
                    sed -i.bak -E 's/console\.(log|error|warn|info|debug|trace|dir|time|timeEnd|assert|table|group|groupEnd)\([^)]*\);?//g' "$file"
                    
                    # Clean up empty lines left behind
                    sed -i.bak2 -E '/^\s*$/d' "$file"
                    
                    rm -f "${file}.bak" "${file}.bak2"
                fi
                
                count=$((count + file_count))
            fi
        fi
    done
    
    echo -e "  ${GREEN}Removed $count console statements from HTML files${NC}"
}

# Remove Python logging statements
remove_python_logs() {
    echo -e "\n${YELLOW}Removing Python logging statements...${NC}"
    
    local files=$(find . -type f -name "*.py" \
                  -not -path "*/venv/*" \
                  -not -path "*/.venv/*" \
                  -not -path "*/env/*" \
                  -not -path "*/__pycache__/*" \
                  -not -path "*/migrations/*")
    
    local count=0
    for file in $files; do
        if [[ -f "$file" ]]; then
            # Count logging statements
            local logger_count=$(grep -E "logger\.(debug|info|warning|error|critical)" "$file" 2>/dev/null | wc -l || echo "0")
            local logging_count=$(grep -E "logging\.(debug|info|warning|error|critical)" "$file" 2>/dev/null | wc -l || echo "0")
            local print_count=$(grep -E "^\s*print\(" "$file" 2>/dev/null | wc -l || echo "0")
            local file_count=$((logger_count + logging_count + print_count))
            
            if [[ $file_count -gt 0 ]]; then
                echo "  Processing: $file (found $file_count log statements)"
                
                if [[ "$DRY_RUN" == false ]]; then
                    # Remove logger statements
                    sed -i.bak -E '/^\s*logger\.(debug|info|warning|error|critical)\(/d' "$file"
                    
                    # Remove logging statements
                    sed -i.bak2 -E '/^\s*logging\.(debug|info|warning|error|critical)\(/d' "$file"
                    
                    # Remove print statements (be careful - only standalone prints)
                    sed -i.bak3 -E '/^\s*print\(/d' "$file"
                    
                    # Remove multi-line logging calls
                    perl -i.bak4 -0pe 's/\s*(logger|logging)\.(debug|info|warning|error|critical)\([^)]*\)\s*\n?//gms' "$file"
                    
                    # Clean up backup files
                    rm -f "${file}.bak" "${file}.bak2" "${file}.bak3" "${file}.bak4"
                fi
                
                count=$((count + file_count))
            fi
        fi
    done
    
    echo -e "  ${GREEN}Removed $count logging statements from Python files${NC}"
}

# Remove import statements that are no longer needed
cleanup_imports() {
    echo -e "\n${YELLOW}Cleaning up unused import statements...${NC}"
    
    if [[ "$DRY_RUN" == false ]]; then
        # Remove console import in TypeScript if no longer used
        find . -type f \( -name "*.ts" -o -name "*.tsx" \) \
             -not -path "*/node_modules/*" \
             -exec grep -l "^import.*console" {} \; | while read file; do
            if ! grep -q "console\." "$file"; then
                sed -i.bak '/^import.*console/d' "$file"
                rm -f "${file}.bak"
                echo "  Removed unused console import from: $file"
            fi
        done
        
        # Remove logging imports in Python if no longer used
        find . -type f -name "*.py" \
             -not -path "*/venv/*" \
             -not -path "*/.venv/*" | while read file; do
            # Check if logging is imported but not used
            if grep -q "^import logging" "$file" && ! grep -q "logging\." "$file"; then
                sed -i.bak '/^import logging/d' "$file"
                rm -f "${file}.bak"
                echo "  Removed unused logging import from: $file"
            fi
            
            # Check if logger is imported but not used
            if grep -q "from.*import.*logger" "$file" && ! grep -q "logger\." "$file"; then
                sed -i.bak '/from.*import.*logger/d' "$file"
                rm -f "${file}.bak"
                echo "  Removed unused logger import from: $file"
            fi
        done
    fi
}

# Main execution
main() {
    echo -e "${GREEN}=== Log Removal Tool ===${NC}"
    echo "This will remove all logging statements from your codebase"
    echo "Affected file types: .js, .ts, .jsx, .tsx, .html, .py"
    echo ""
    
    # Show current state
    echo -e "${YELLOW}Current logging statements:${NC}"
    echo "  JavaScript/TypeScript console.*: $(rg "console\." --type js --type ts . 2>/dev/null | wc -l || echo "0")"
    echo "  Python logger/logging: $(rg "(logger\.|logging\.)" --type py . 2>/dev/null | wc -l || echo "0")"
    echo "  Python print statements: $(rg "^\s*print\(" --type py . 2>/dev/null | wc -l || echo "0")"
    echo ""
    
    if [[ "$DRY_RUN" == false ]]; then
        read -p "Are you sure you want to remove all logging? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${RED}Aborted${NC}"
            exit 1
        fi
    fi
    
    # Remove logs from different file types
    remove_js_logs
    remove_html_logs
    remove_python_logs
    cleanup_imports
    
    echo -e "\n${GREEN}✅ Log removal complete!${NC}"
    
    if [[ "$DRY_RUN" == true ]]; then
        echo -e "${YELLOW}This was a dry run. Run without --dry-run to actually remove logs.${NC}"
    else
        echo -e "${YELLOW}Tip: Run 'git diff' to review changes${NC}"
    fi
}

# Run main function
main