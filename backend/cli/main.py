import click
from pathlib import Path
from backend.analysis import AnalysisOrchestrator, ScanRequest
from backend.cli.slither_wrapper import SlitherWrapper
import json
from dataclasses import asdict

@click.group()
def cli():
    """BlockScope - Smart Contract Vulnerability Scanner"""
    pass

@cli.command()
@click.argument('contract_file', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Choice(['json', 'text']), default='text',
              help='Output format (default: text)')
@click.option('--contract-name', '-n', default=None,
              help='Contract name (auto-detected if not provided)')
def scan(contract_file, output, contract_name):
    """
    Scan a Solidity contract for vulnerabilities.
    
    USAGE:
        python -m backend.cli.main scan contract.sol
        python -m backend.cli.main scan contract.sol -o json
        python -m backend.cli.main scan contract.sol -n MyContract
    """
    
    try:
        # 1. Load source code from file
        file_path = Path(contract_file)
        source_code = file_path.read_text()
        
        # 2. Detect contract name if not provided
        if not contract_name:
            contract_name = file_path.stem  # Use filename without extension
        
        # 3. Create ScanRequest
        request = ScanRequest(
            source_code=source_code,
            contract_name=contract_name,
            file_path=str(file_path)
        )
        
        # 4. Initialize orchestrator and run scan
        orchestrator = AnalysisOrchestrator(rules=[])  # YOU will provide rules
        result = orchestrator.analyze(request)
        
        # 5. Format and print output
        if output == 'json':
            import json
            output_data = {
                "contract_name": result.contract_name,
                "vulnerabilities_count": result.vulnerabilities_count,
                "severity_breakdown": result.severity_breakdown,
                "overall_score": result.overall_score,
                "summary": result.summary,
                "findings": [asdict(f) for f in result.findings]
            }
            click.echo(json.dumps(output_data, indent=2))
        
        else:  # text output
            click.secho(f"\n{'='*60}", fg='cyan')
            click.secho(f"📋 CONTRACT: {result.contract_name}", fg='cyan', bold=True)
            click.secho(f"{'='*60}\n", fg='cyan')
            
            click.secho(f"Score: {result.overall_score}/100", 
                       fg='green' if result.overall_score >= 80 else 'yellow' if result.overall_score >= 50 else 'red',
                       bold=True)
            click.echo(f"Summary: {result.summary}")
            
            if result.severity_breakdown:
                click.echo("\nSeverity Breakdown:")
                for severity, count in result.severity_breakdown.items():
                    color = 'red' if severity == 'critical' else 'yellow' if severity == 'high' else 'blue'
                    click.secho(f"  {severity.upper()}: {count}", fg=color)
            
            if result.findings:
                click.echo(f"\nFindings ({len(result.findings)}):")
                for i, finding in enumerate(result.findings, 1):
                    click.echo(f"  {i}. {finding.title} ({finding.severity})")
                    click.echo(f"     {finding.description}\n")
            else:
                click.secho("\n✅ No vulnerabilities found!", fg='green')
            
            click.secho(f"\n{'='*60}\n", fg='cyan')
    
    except FileNotFoundError:
        click.secho(f"❌ File not found: {contract_file}", fg='red')
        raise SystemExit(1)
    
    except Exception as e:
        click.secho(f"❌ Error scanning contract: {str(e)}", fg='red')
        raise SystemExit(1)

if __name__ == '__main__':
    cli()
