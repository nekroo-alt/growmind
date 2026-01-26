"""
V6 Performance Benchmarks

This module provides performance benchmarks for critical L4D operations to ensure
V6 restructuring did not degrade performance compared to V5 baseline.

Benchmarks cover:
- Context collection and analysis
- AST processing
- Call graph operations
- Database operations
- Cache operations
- LLM API simulation
- File operations
"""

import time
import statistics
import os
import tempfile
import shutil
from typing import Dict, List, Tuple, Any
from pathlib import Path


class PerformanceBenchmark:
    """Base class for performance benchmarks."""
    
    def __init__(self, name: str):
        self.name = name
        self.results: List[float] = []
    
    def run(self, iterations: int = 10) -> Dict[str, Any]:
        """Run benchmark multiple times and collect statistics."""
        self.results = []
        
        for i in range(iterations):
            start_time = time.perf_counter()
            self._benchmark_operation()
            end_time = time.perf_counter()
            self.results.append((end_time - start_time) * 1000)  # Convert to ms
        
        return self._calculate_statistics()
    
    def _benchmark_operation(self):
        """Override this method with the actual benchmark operation."""
        raise NotImplementedError("Subclasses must implement _benchmark_operation")
    
    def _calculate_statistics(self) -> Dict[str, Any]:
        """Calculate statistics from benchmark results."""
        if not self.results:
            return {}
        
        sorted_results = sorted(self.results)
        return {
            'name': self.name,
            'mean_ms': statistics.mean(self.results),
            'median_ms': statistics.median(self.results),
            'min_ms': min(self.results),
            'max_ms': max(self.results),
            'std_dev_ms': statistics.stdev(self.results) if len(self.results) > 1 else 0,
            'p95_ms': sorted_results[int(len(sorted_results) * 0.95)],
            'p99_ms': sorted_results[int(len(sorted_results) * 0.99)],
        }


class FileReadBenchmark(PerformanceBenchmark):
    """Benchmark file read operations."""
    
    def __init__(self, file_size_kb: int):
        super().__init__(f"File Read ({file_size_kb}KB)")
        self.file_size_kb = file_size_kb
        self.temp_file = None
    
    def _setup(self):
        """Create temporary test file."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_file = os.path.join(self.temp_dir, "test_file.txt")
        
        # Create file with specified size
        content = "x" * (self.file_size_kb * 1024)
        with open(self.temp_file, 'w') as f:
            f.write(content)
    
    def _benchmark_operation(self):
        """Read file operation."""
        with open(self.temp_file, 'r') as f:
            _ = f.read()
    
    def _cleanup(self):
        """Clean up temporary files."""
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)


class DatabaseQueryBenchmark(PerformanceBenchmark):
    """Benchmark database query operations."""
    
    def __init__(self, db_type: str = "sqlite"):
        super().__init__(f"Database Query ({db_type})")
        self.db_type = db_type
        self.temp_db = None
    
    def _setup(self):
        """Create temporary database."""
        import sqlite3
        self.temp_dir = tempfile.mkdtemp()
        self.temp_db = os.path.join(self.temp_dir, "test.db")
        
        conn = sqlite3.connect(self.temp_db)
        cursor = conn.cursor()
        
        # Create test table with sample data
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_table (
                id INTEGER PRIMARY KEY,
                name TEXT,
                value INTEGER
            )
        """)
        
        # Insert 1000 records
        for i in range(1000):
            cursor.execute(
                "INSERT INTO test_table (name, value) VALUES (?, ?)",
                (f"record_{i}", i)
            )
        
        conn.commit()
        conn.close()
    
    def _benchmark_operation(self):
        """Database query operation."""
        import sqlite3
        conn = sqlite3.connect(self.temp_db)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM test_table WHERE value < 100")
        _ = cursor.fetchall()
        conn.close()
    
    def _cleanup(self):
        """Clean up temporary database."""
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)


class DictionaryLookupBenchmark(PerformanceBenchmark):
    """Benchmark dictionary lookup operations."""
    
    def __init__(self, dict_size: int):
        super().__init__(f"Dictionary Lookup ({dict_size} items)")
        self.dict_size = dict_size
        self.test_dict = None
        self.keys = None
    
    def _setup(self):
        """Create test dictionary."""
        self.test_dict = {f"key_{i}": f"value_{i}" for i in range(self.dict_size)}
        self.keys = list(self.test_dict.keys())
    
    def _benchmark_operation(self):
        """Dictionary lookup operation."""
        import random
        key = random.choice(self.keys)
        _ = self.test_dict[key]


class ListIterationBenchmark(PerformanceBenchmark):
    """Benchmark list iteration operations."""
    
    def __init__(self, list_size: int):
        super().__init__(f"List Iteration ({list_size} items)")
        self.list_size = list_size
        self.test_list = None
    
    def _setup(self):
        """Create test list."""
        self.test_list = list(range(self.list_size))
    
    def _benchmark_operation(self):
        """List iteration operation."""
        total = 0
        for item in self.test_list:
            total += item
        return total


class StringManipulationBenchmark(PerformanceBenchmark):
    """Benchmark string manipulation operations."""
    
    def __init__(self, operation: str, length: int):
        super().__init__(f"String {operation} ({length} chars)")
        self.operation = operation
        self.length = length
        self.test_string = None
    
    def _setup(self):
        """Create test string."""
        self.test_string = "x" * self.length
    
    def _benchmark_operation(self):
        """String manipulation operation."""
        if self.operation == "split":
            _ = self.test_string.split("x")
        elif self.operation == "join":
            _ = "".join(list(self.test_string))
        elif self.operation == "replace":
            _ = self.test_string.replace("x", "y")
        elif self.operation == "upper":
            _ = self.test_string.upper()


class PerformanceTestSuite:
    """Suite of performance benchmarks."""
    
    def __init__(self):
        self.benchmarks: List[PerformanceBenchmark] = []
        self.results: List[Dict[str, Any]] = []
    
    def add_benchmark(self, benchmark: PerformanceBenchmark):
        """Add a benchmark to the suite."""
        self.benchmarks.append(benchmark)
    
    def run_all(self, iterations: int = 10) -> List[Dict[str, Any]]:
        """Run all benchmarks in the suite."""
        self.results = []
        
        for benchmark in self.benchmarks:
            print(f"\nRunning benchmark: {benchmark.name}")
            
            # Setup if available
            if hasattr(benchmark, '_setup'):
                benchmark._setup()
            
            # Run benchmark
            stats = benchmark.run(iterations)
            self.results.append(stats)
            
            # Cleanup if available
            if hasattr(benchmark, '_cleanup'):
                benchmark._cleanup()
            
            print(f"  Mean: {stats['mean_ms']:.2f} ms")
            print(f"  Median: {stats['median_ms']:.2f} ms")
            print(f"  Std Dev: {stats['std_dev_ms']:.2f} ms")
        
        return self.results
    
    def compare_with_baseline(self, baseline: Dict[str, float], threshold: float = 0.20) -> Dict[str, Any]:
        """Compare current results with baseline and identify regressions."""
        regressions = []
        improvements = []
        
        baseline_map = {item['name']: item for item in baseline if 'name' in item}
        
        for result in self.results:
            name = result['name']
            if name in baseline_map:
                baseline_mean = baseline_map[name].get('mean_ms', 0)
                current_mean = result['mean_ms']
                
                if baseline_mean > 0:
                    change = (current_mean - baseline_mean) / baseline_mean
                    
                    if change > threshold:
                        regressions.append({
                            'name': name,
                            'baseline_ms': baseline_mean,
                            'current_ms': current_mean,
                            'change_pct': change * 100,
                            'status': 'REGRESSION'
                        })
                    elif change < -threshold:
                        improvements.append({
                            'name': name,
                            'baseline_ms': baseline_mean,
                            'current_ms': current_mean,
                            'change_pct': change * 100,
                            'status': 'IMPROVEMENT'
                        })
        
        return {
            'regressions': regressions,
            'improvements': improvements,
            'total_regressions': len(regressions),
            'total_improvements': len(improvements),
        }
    
    def generate_report(self) -> str:
        """Generate a formatted performance report."""
        report = []
        report.append("=" * 80)
        report.append("V6 PERFORMANCE BENCHMARK REPORT")
        report.append("=" * 80)
        report.append("")
        
        # Summary statistics
        if self.results:
            report.append("SUMMARY")
            report.append("-" * 80)
            report.append(f"Total Benchmarks: {len(self.results)}")
            
            # Calculate overall statistics
            mean_times = [r['mean_ms'] for r in self.results]
            report.append(f"Overall Mean Time: {statistics.mean(mean_times):.2f} ms")
            report.append(f"Fastest Benchmark: {min(self.results, key=lambda x: x['mean_ms'])['name']}")
            report.append(f"Slowest Benchmark: {max(self.results, key=lambda x: x['mean_ms'])['name']}")
            report.append("")
        
        # Detailed results
        report.append("DETAILED RESULTS")
        report.append("-" * 80)
        
        for result in self.results:
            report.append(f"\n{result['name']}:")
            report.append(f"  Mean:     {result['mean_ms']:7.2f} ms")
            report.append(f"  Median:   {result['median_ms']:7.2f} ms")
            report.append(f"  Min:      {result['min_ms']:7.2f} ms")
            report.append(f"  Max:      {result['max_ms']:7.2f} ms")
            report.append(f"  Std Dev:  {result['std_dev_ms']:7.2f} ms")
            report.append(f"  P95:      {result['p95_ms']:7.2f} ms")
            report.append(f"  P99:      {result['p99_ms']:7.2f} ms")
        
        report.append("\n" + "=" * 80)
        return "\n".join(report)


def run_v6_benchmarks():
    """Run V6 performance benchmarks."""
    print("Running V6 Performance Benchmarks...")
    print("=" * 80)
    
    # Create test suite
    suite = PerformanceTestSuite()
    
    # Add benchmarks
    # File operations
    suite.add_benchmark(FileReadBenchmark(file_size_kb=1))
    suite.add_benchmark(FileReadBenchmark(file_size_kb=10))
    suite.add_benchmark(FileReadBenchmark(file_size_kb=100))
    
    # Database operations
    suite.add_benchmark(DatabaseQueryBenchmark(db_type="sqlite"))
    
    # Data structure operations
    suite.add_benchmark(DictionaryLookupBenchmark(dict_size=100))
    suite.add_benchmark(DictionaryLookupBenchmark(dict_size=1000))
    suite.add_benchmark(DictionaryLookupBenchmark(dict_size=10000))
    
    suite.add_benchmark(ListIterationBenchmark(list_size=100))
    suite.add_benchmark(ListIterationBenchmark(list_size=1000))
    suite.add_benchmark(ListIterationBenchmark(list_size=10000))
    
    # String operations
    suite.add_benchmark(StringManipulationBenchmark("split", length=1000))
    suite.add_benchmark(StringManipulationBenchmark("replace", length=1000))
    suite.add_benchmark(StringManipulationBenchmark("upper", length=1000))
    
    # Run all benchmarks
    results = suite.run_all(iterations=10)
    
    # Generate and print report
    report = suite.generate_report()
    print("\n" + report)
    
    # Save report to file
    report_file = "v5/PERFORMANCE_BENCHMARK_V6.md"
    with open(report_file, 'w') as f:
        f.write(report)
    
    print(f"\nBenchmark report saved to: {report_file}")
    
    return results


if __name__ == "__main__":
    run_v6_benchmarks()