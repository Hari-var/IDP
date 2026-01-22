import json
from fastapi import APIRouter

router = APIRouter(prefix="/benchmark", tags=["Benchmark"])


@router.get("/run")
def run_benchmark():
    """Run benchmark test manually."""
    from app.helpers.benchmark import run_manual_benchmark
    run_manual_benchmark()
    return {"message": "Benchmark test completed. Check benchmark.log for results."}


@router.get("/results")
def get_benchmark_results():
    """Get all benchmark results."""
    try:
        with open('benchmark_results.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {"message": "No benchmark results found"}


@router.get("/results/latest")
def get_latest_benchmark_results():
    """Get latest benchmark results only."""
    try:
        with open('benchmark_results.json', 'r') as f:
            all_results = json.load(f)
            return all_results[-1] if all_results else {"message": "No results found"}
    except FileNotFoundError:
        return {"message": "No benchmark results found"}
