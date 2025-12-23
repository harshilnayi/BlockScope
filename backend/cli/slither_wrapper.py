"""Wrapper around Slither for AST parsing."""
from typing import Optional
from pathlib import Path


class SlitherWrapper:
    """Wrapper for Slither contract analysis."""
    
    def __init__(self):
        """Initialize Slither wrapper."""
        try:
            from slither import Slither
            self.Slither = Slither
            self.available = True
        except ImportError:
            print("⚠️  Slither not installed. Install with: pip install slither-analyzer")
            self.available = False
    
    def parse_contract(self, file_path: str):
        """
        Parse Solidity contract using Slither.
        
        Args:
            file_path: Path to Solidity file
        
        Returns:
            Slither object with AST
        """
        if not self.available:
            raise RuntimeError("Slither not available. Install: pip install slither-analyzer")
        
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Contract file not found: {file_path}")
        
        try:
            # This will parse the contract
            slither = self.Slither(str(file_path))
            print(f"✅ Successfully parsed: {file_path.name}")
            return slither
        except Exception as e:
            print(f"❌ Error parsing contract: {e}")
            raise
    
    def get_ast_nodes(self, slither_obj):
        """
        Get AST nodes from parsed contract.
        
        Args:
            slither_obj: Slither object
        
        Returns:
            List of contract objects and their functions
        """
        if not slither_obj:
            return None
        
        return slither_obj.contracts
