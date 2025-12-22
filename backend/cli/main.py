"""BlockScope CLI tool."""
import click
from pathlib import Path
from typing import Optional

@click.group()
def cli():
    """BlockScope - Smart Contract Vulnerability Scanner."""
    pass

@cli.command()
@click.argument('contract_file', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Choice(['json', 'txt']), default='txt',
              help='Output format')
def scan(contract_file: str, output: str):
    """Scan a Solidity contract for vulnerabilities."""
    
    file_path = Path(contract_file)
    
    if not file_path.exists():
        click.echo(f"Error: File {contract_file} not found", err=True)
        return
    
    with open(file_path, 'r') as f:
        contract_code = f.read()
    
    click.echo(f"🔍 Scanning {contract_file}...")
    
    # TODO: Integrate with analysis engine
    # findings = scanner.scan(contract_code)
    
    click.echo("✅ Scan complete!")

if __name__ == '__main__':
    cli()
