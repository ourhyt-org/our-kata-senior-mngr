#!/bin/bash
set -e

echo "🧹 Cleaning previous artifacts..."
rm -rf packages
rm -f kata-lambda.zip
mkdir -p packages

echo "📦 Installing dependencies into packages/..."
pip install -r requirements.txt -t packages/

echo "🗜️ Building ZIP..."
cd packages
zip -r9 ../kata-lambda.zip .
cd ..

zip -r9 kata-lambda.zip app/

echo "✅ DONE: kata-lambda.zip ready for deployment"