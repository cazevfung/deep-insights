"""Research session management.

This module handles saving and loading research sessions, including
the scratchpad and all findings.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger


class ResearchSession:
    """Manages research session state and persistence."""
    
    def __init__(self, session_id: Optional[str] = None, base_path: Optional[Path] = None):
        """
        Initialize research session.
        
        Args:
            session_id: Unique session identifier (auto-generated if not provided)
            base_path: Base path for storing sessions (defaults to data/research/sessions/)
        """
        if session_id is None:
            # Generate session ID from timestamp
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        self.session_id = session_id
        
        if base_path is None:
            # Default to project root/data/research/sessions/
            # __file__ = research/session.py; parent = research/; parent = project root
            self.base_path = Path(__file__).parent.parent / "data" / "research" / "sessions"
        else:
            self.base_path = Path(base_path)
        
        # Create directory if it doesn't exist
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Session data
        self.scratchpad: Dict[str, Any] = {}
        self.metadata: Dict[str, Any] = {
            "session_id": self.session_id,
            "created_at": datetime.now().isoformat(),
            "batch_id": None,
            "selected_goal": None,
            "research_plan": None,
            "status": "initialized"
        }
        
        # Session file path
        self.session_file = self.base_path / f"session_{session_id}.json"
        
        logger.info(f"Initialized ResearchSession: {session_id}")
    
    def save(self):
        """Save session to disk."""
        session_data = {
            "metadata": self.metadata,
            "scratchpad": self.scratchpad
        }
        
        try:
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Saved session to {self.session_file}")
        except Exception as e:
            logger.error(f"Error saving session: {str(e)}")
            raise
    
    @classmethod
    def load(cls, session_id: str, base_path: Optional[Path] = None) -> 'ResearchSession':
        """
        Load existing session from disk.
        
        Args:
            session_id: Session identifier
            base_path: Base path for sessions
            
        Returns:
            Loaded ResearchSession instance
        """
        if base_path is None:
            base_path = Path(__file__).parent.parent / "data" / "research" / "sessions"
        
        session_file = Path(base_path) / f"session_{session_id}.json"
        
        if not session_file.exists():
            raise FileNotFoundError(f"Session file not found: {session_file}")
        
        session = cls(session_id=session_id, base_path=base_path)
        
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            session.metadata = session_data.get("metadata", {})
            session.scratchpad = session_data.get("scratchpad", {})
            
            logger.info(f"Loaded session from {session_file}")
        except Exception as e:
            logger.error(f"Error loading session: {str(e)}")
            raise
        
        return session
    
    def update_scratchpad(
        self, 
        step_id: int, 
        findings: Dict[str, Any], 
        insights: str = "", 
        confidence: float = 0.0,
        sources: Optional[List[str]] = None,
        *,
        autosave: bool = True
    ):
        """
        Update scratchpad with findings from a step.
        
        Args:
            step_id: Step identifier
            findings: Structured findings
            insights: Key insights summary
            confidence: Confidence score (0.0-1.0)
            sources: List of source link_ids (enhancement #2)
        """
        scratchpad_entry = {
            "step_id": step_id,
            "findings": findings,
            "insights": insights,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat()
        }
        
        # Add sources if provided (enhancement #2)
        if sources:
            scratchpad_entry["sources"] = sources
        
        self.scratchpad[f"step_{step_id}"] = scratchpad_entry
        
        # Auto-save can be throttled by caller for performance
        if autosave:
            self.save()
        
        logger.debug(f"Updated scratchpad for step {step_id}")
    
    def get_scratchpad_summary(self) -> str:
        """
        Get scratchpad contents as a formatted string for prompts.
        
        Returns:
            Formatted scratchpad string with source attribution (enhancement #2)
        """
        if not self.scratchpad:
            return "暂无发现。"
        
        summary_parts = []
        for step_key in sorted(self.scratchpad.keys()):
            step_data = self.scratchpad[step_key]
            step_summary = f"步骤 {step_data['step_id']}: {step_data.get('insights', '')}\n"
            
            # Extract findings with points of interest
            findings = step_data.get('findings', {})
            
            # Add summary if available
            if isinstance(findings, dict) and 'summary' in findings:
                step_summary += f"摘要: {findings['summary']}\n"
            
            # Add points of interest if available
            if isinstance(findings, dict) and 'points_of_interest' in findings:
                poi = findings['points_of_interest']
                poi_summary = []
                
                if poi.get('key_claims'):
                    claims_count = len(poi['key_claims'])
                    poi_summary.append(f"关键论点: {claims_count} 个")
                
                if poi.get('notable_evidence'):
                    evidence_count = len(poi['notable_evidence'])
                    poi_summary.append(f"重要证据: {evidence_count} 个")
                
                if poi.get('controversial_topics'):
                    topics_count = len(poi['controversial_topics'])
                    poi_summary.append(f"争议话题: {topics_count} 个")
                
                if poi.get('surprising_insights'):
                    insights_count = len(poi['surprising_insights'])
                    poi_summary.append(f"意外洞察: {insights_count} 个")
                
                if poi.get('specific_examples'):
                    examples_count = len(poi['specific_examples'])
                    poi_summary.append(f"具体例子: {examples_count} 个")
                
                if poi.get('open_questions'):
                    questions_count = len(poi['open_questions'])
                    poi_summary.append(f"开放问题: {questions_count} 个")
                
                if poi_summary:
                    step_summary += f"兴趣点: {', '.join(poi_summary)}\n"
                
                # Extract and format quotes/examples prominently (Solution 9)
                quotes_section = "\n**重要引述和例子**:\n"
                quotes_found = False
                
                # Key claims with quotes
                for claim in poi.get('key_claims', [])[:5]:
                    if isinstance(claim, dict) and claim.get('claim'):
                        quotes_found = True
                        quotes_section += f"- \"{claim['claim']}\""
                        if claim.get('supporting_evidence'):
                            evidence_text = claim['supporting_evidence']
                            if len(evidence_text) > 100:
                                evidence_text = evidence_text[:100] + "..."
                            quotes_section += f" (证据: {evidence_text})"
                        quotes_section += "\n"
                
                # Notable evidence quotes
                for evidence in poi.get('notable_evidence', [])[:5]:
                    if isinstance(evidence, dict) and evidence.get('quote'):
                        quotes_found = True
                        quotes_section += f"- \"{evidence['quote']}\""
                        if evidence.get('description'):
                            desc_text = evidence['description']
                            if len(desc_text) > 80:
                                desc_text = desc_text[:80] + "..."
                            quotes_section += f" ({desc_text})"
                        quotes_section += "\n"
                
                # Specific examples
                for example in poi.get('specific_examples', [])[:5]:
                    if isinstance(example, dict) and example.get('example'):
                        quotes_found = True
                        quotes_section += f"- 例子: {example['example']}"
                        if example.get('context'):
                            context_text = example['context']
                            if len(context_text) > 80:
                                context_text = context_text[:80] + "..."
                            quotes_section += f" (上下文: {context_text})"
                        quotes_section += "\n"
                
                if quotes_found:
                    step_summary += quotes_section + "\n"
            
            # Add full findings JSON
            step_summary += f"发现: {json.dumps(findings, ensure_ascii=False, indent=2)}"
            
            # Add source information if available (enhancement #2)
            if 'sources' in step_data and step_data['sources']:
                sources_str = ", ".join(step_data['sources'])
                step_summary += f"\n来源: {sources_str}"
            
            summary_parts.append(step_summary)
        
        return "\n\n".join(summary_parts)
    
    def set_metadata(self, key: str, value: Any):
        """Update metadata."""
        self.metadata[key] = value
        self.metadata["updated_at"] = datetime.now().isoformat()
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata value."""
        return self.metadata.get(key, default)

