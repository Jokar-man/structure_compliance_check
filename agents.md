# Agents Documentation

## Overview
This document describes the agents and automated components used in the structure compliance check system for BIM models.

## Agent Architecture

### 1. Beam Compliance Agent
**Location**: `beam_check/`
**Purpose**: Validates beam structural elements against compliance standards
**Responsibilities**:
- Check beam dimensions and specifications
- Verify load-bearing capacity
- Validate reinforcement requirements
- Generate compliance reports for beam elements

### 2. Column Compliance Agent
**Location**: `column_check/`
**Purpose**: Ensures column elements meet structural requirements
**Responsibilities**:
- Validate column dimensions and placement
- Check load distribution
- Verify structural integrity
- Assess alignment and positioning

### 3. Slab Compliance Agent
**Location**: `slab_check/`
**Purpose**: Analyzes slab elements for compliance
**Responsibilities**:
- Verify slab thickness and coverage
- Check reinforcement spacing
- Validate load distribution
- Ensure proper connection points

### 4. Wall Compliance Agent
**Location**: `walls_check/`
**Purpose**: Validates wall structures and specifications
**Responsibilities**:
- Check wall thickness and height
- Verify structural connections
- Validate material specifications
- Ensure proper reinforcement

## Agent Coordination

### Main Application Controller
**Location**: `basic_app/`
**Purpose**: Orchestrates all compliance checking agents

The main application coordinates between different specialized agents to provide:
- Unified compliance reporting
- Cross-element validation
- Consolidated results
- User interface for interaction

## Workflow

1. **Model Ingestion**: BIM model is loaded into the system
2. **Element Extraction**: Structural elements are identified and categorized
3. **Agent Dispatch**: Appropriate compliance agents are invoked for each element type
4. **Parallel Processing**: Multiple agents can run simultaneously on different elements
5. **Result Aggregation**: All agent results are collected and consolidated
6. **Report Generation**: Final compliance report is generated

## Future Agent Extensions

Potential additional agents for future development:
- Foundation compliance agent
- Connection/joint validation agent
- Material specification checker
- Code compliance validator (regional building codes)
- Risk assessment agent

## Agent Communication Protocol

Agents communicate through standardized interfaces:
- Input: BIM model elements in IFC format
- Output: Compliance status (Pass/Fail/Warning)
- Reports: JSON-formatted detailed findings

## Configuration

Agent behavior can be configured through:
- Compliance standards (regional codes)
- Tolerance levels
- Validation thresholds
- Reporting verbosity

---
*For more information on each specific agent, refer to the README.md in their respective directories.*
