#!/bin/bash

COMPOSE_FILE="docker-compose.yml"

show_usage() {
    echo "ER_CHAI Management Script"
    echo ""
    echo "Usage: ./manage.sh [command]"
    echo ""
    echo "Commands:"
    echo "  start      - Start all services"
    echo "  stop       - Stop all services"
    echo "  restart    - Restart all services"
    echo "  status     - Show service status"
    echo "  logs       - Show logs (all services)"
    echo "  logs-backend   - Show backend logs only"
    echo "  logs-frontend  - Show frontend logs only"
    echo "  update     - Pull latest code and rebuild"
    echo "  clean      - Stop and remove all containers, volumes"
    echo "  shell-backend  - Open shell in backend container"
    echo "  shell-frontend - Open shell in frontend container"
    echo ""
}

case "$1" in
    start)
        echo "Starting ER_CHAI services..."
        docker-compose -f $COMPOSE_FILE up -d
        echo "✅ Services started"
        docker-compose -f $COMPOSE_FILE ps
        ;;
    
    stop)
        echo "Stopping ER_CHAI services..."
        docker-compose -f $COMPOSE_FILE down
        echo "✅ Services stopped"
        ;;
    
    restart)
        echo "Restarting ER_CHAI services..."
        docker-compose -f $COMPOSE_FILE restart
        echo "✅ Services restarted"
        docker-compose -f $COMPOSE_FILE ps
        ;;
    
    status)
        echo "ER_CHAI Service Status:"
        echo ""
        docker-compose -f $COMPOSE_FILE ps
        echo ""
        echo "Container Health:"
        docker ps --filter "name=er_chai" --format "table {{.Names}}\t{{.Status}}"
        ;;
    
    logs)
        echo "Showing logs (Ctrl+C to exit)..."
        docker-compose -f $COMPOSE_FILE logs -f
        ;;
    
    logs-backend)
        echo "Showing backend logs (Ctrl+C to exit)..."
        docker-compose -f $COMPOSE_FILE logs -f backend
        ;;
    
    logs-frontend)
        echo "Showing frontend logs (Ctrl+C to exit)..."
        docker-compose -f $COMPOSE_FILE logs -f frontend
        ;;
    
    update)
        echo "Updating ER_CHAI..."
        echo "Step 1/4: Pulling latest code..."
        cd ../..
        git pull origin main
        cd deployment/lightsail
        
        echo "Step 2/4: Stopping services..."
        docker-compose -f $COMPOSE_FILE down
        
        echo "Step 3/4: Rebuilding containers..."
        docker-compose -f $COMPOSE_FILE build --no-cache
        
        echo "Step 4/4: Starting services..."
        docker-compose -f $COMPOSE_FILE up -d
        
        echo "✅ Update complete"
        docker-compose -f $COMPOSE_FILE ps
        ;;
    
    clean)
        echo "⚠️  This will remove all containers and volumes!"
        read -p "Are you sure? (yes/no): " confirm
        if [ "$confirm" = "yes" ]; then
            echo "Cleaning up..."
            docker-compose -f $COMPOSE_FILE down -v
            docker system prune -f
            echo "✅ Cleanup complete"
        else
            echo "Cancelled"
        fi
        ;;
    
    shell-backend)
        echo "Opening shell in backend container..."
        docker exec -it er_chai_backend /bin/bash
        ;;
    
    shell-frontend)
        echo "Opening shell in frontend container..."
        docker exec -it er_chai_frontend /bin/sh
        ;;
    
    *)
        show_usage
        exit 1
        ;;
esac
