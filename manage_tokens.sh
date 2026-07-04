#!/bin/bash
# Secure Token Distribution for External Teams
# Generates unique tokens, manages access, and logs distribution

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
TOKEN_DIR="/root/dojobay/tokens"
TOKEN_LOG="/root/dojobay/tokens/distribution_log.txt"
MASTER_TOKEN="e3a15e137191a5016644dfb6f6fe4f7c7dac2156157a0b4bfcd73bc5614727d7"

# Ensure directories exist
mkdir -p "$TOKEN_DIR"

log_distribution() {
    local message="$1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $message" >> "$TOKEN_LOG"
}

generate_token() {
    openssl rand -hex 32
}

create_team_token() {
    local team_name="$1"
    local token_file="$TOKEN_DIR/${team_name}.token"
    
    if [ -z "$team_name" ]; then
        echo -e "${RED}Team name is required${NC}"
        return 1
    fi
    
    if [ -f "$token_file" ]; then
        echo -e "${YELLOW}Token for team '$team_name' already exists${NC}"
        read -p "Regenerate? (y/n): " regenerate
        if [ "$regenerate" != "y" ]; then
            return 1
        fi
    fi
    
    local token=$(generate_token)
    echo "$token" > "$token_file"
    chmod 600 "$token_file"
    
    echo -e "${GREEN}✓ Token created for team: $team_name${NC}"
    echo "Token: $token"
    
    log_distribution "Created token for team: $team_name"
    
    # Show usage example
    echo ""
    echo -e "${BLUE}Usage Example:${NC}"
    echo "curl -H \"Authorization: Bearer $token\" \\"
    echo "     https://your-domain.com/api/dojos"
    echo ""
    
    return 0
}

list_tokens() {
    echo -e "${BLUE}Registered Tokens:${NC}"
    echo ""
    
    local count=0
    for token_file in "$TOKEN_DIR"/*.token; do
        if [ -f "$token_file" ]; then
            local team_name=$(basename "$token_file" .token)
            local token=$(cat "$token_file")
            local created=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" "$token_file" 2>/dev/null || stat -c "%y" "$token_file" 2>/dev/null | cut -d' ' -f1,2)
            
            echo "Team: $team_name"
            echo "Token: $(echo $token | cut -c1-16)...$(echo $token | tail -c 8)"
            echo "Created: $created"
            echo "---"
            
            ((count++))
        fi
    done
    
    if [ $count -eq 0 ]; then
        echo "No tokens found"
    else
        echo -e "${BLUE}Total: $count tokens${NC}"
    fi
    
    echo ""
}

revoke_token() {
    local team_name="$1"
    local token_file="$TOKEN_DIR/${team_name}.token"
    
    if [ -z "$team_name" ]; then
        echo -e "${RED}Team name is required${NC}"
        return 1
    fi
    
    if [ ! -f "$token_file" ]; then
        echo -e "${RED}Token for team '$team_name' not found${NC}"
        return 1
    fi
    
    read -p "Revoke token for team '$team_name'? (y/n): " confirm
    if [ "$confirm" != "y" ]; then
        return
    fi
    
    local old_token=$(cat "$token_file")
    local new_token=$(generate_token)
    
    # Keep backup
    local backup_file="$TOKEN_DIR/${team_name}.token.revoked.$(date +%s)"
    cp "$token_file" "$backup_file"
    
    # Update with new token
    echo "$new_token" > "$token_file"
    chmod 600 "$token_file"
    
    echo -e "${GREEN}✓ Token revoked and rotated${NC}"
    echo "Old Token: $old_token"
    echo "New Token: $new_token"
    echo "Backup: $backup_file"
    
    log_distribution "Revoked and rotated token for team: $team_name"
    
    echo ""
    echo -e "${YELLOW}Important: Share the new token with the team immediately${NC}"
    
    return 0
}

get_token() {
    local team_name="$1"
    local token_file="$TOKEN_DIR/${team_name}.token"
    
    if [ -z "$team_name" ]; then
        echo -e "${RED}Team name is required${NC}"
        return 1
    fi
    
    if [ ! -f "$token_file" ]; then
        echo -e "${RED}Token for team '$team_name' not found${NC}"
        return 1
    fi
    
    local token=$(cat "$token_file")
    echo -e "${GREEN}Token for team '$team_name':${NC}"
    echo "$token"
    
    log_distribution "Retrieved token for team: $team_name"
    
    return 0
}

show_usage() {
    echo -e "${BLUE}Secure Token Distribution Tool${NC}"
    echo ""
    echo "Usage: $0 <command> [arguments]"
    echo ""
    echo "Commands:"
    echo "  create <team_name>     - Create a new token for a team"
    echo "  list                   - List all registered tokens"
    echo "  get <team_name>        - Get token for a team"
    echo "  revoke <team_name>     - Revoke and rotate token"
    echo "  distribution-log       - Show token distribution log"
    echo ""
    echo "Examples:"
    echo "  $0 create mobile-app"
    echo "  $0 list"
    echo "  $0 get mobile-app"
    echo "  $0 revoke mobile-app"
    echo ""
}

# Main
case "${1:-}" in
    create)
        create_team_token "$2"
        ;;
    list)
        list_tokens
        ;;
    get)
        get_token "$2"
        ;;
    revoke)
        revoke_token "$2"
        ;;
    distribution-log)
        echo -e "${BLUE}Token Distribution Log:${NC}"
        [ -f "$TOKEN_LOG" ] && cat "$TOKEN_LOG" || echo "No log entries"
        ;;
    *)
        show_usage
        ;;
esac
