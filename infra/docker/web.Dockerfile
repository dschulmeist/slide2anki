FROM node:20-alpine

WORKDIR /app

# Copy package files
COPY apps/web/package.json apps/web/package-lock.json* ./

# Install dependencies
RUN npm install

# Copy application code
COPY apps/web .

# Expose port
EXPOSE 3000

# Default command
CMD ["npm", "run", "dev"]
