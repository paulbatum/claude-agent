# Documentation Index

Welcome to the Claude Agent documentation! This folder contains comprehensive, in-depth documentation about every aspect of this project.

## 📖 Documentation Files

### Getting Started

Start here if you're new:

1. **[Querying This Agent](querying-this-agent.md)** - How to ask the agent about itself
   - Best practices for questions
   - Example queries
   - How the self-awareness system works

2. **[Architecture](architecture.md)** - High-level system overview
   - Three-tier architecture
   - Data flow diagrams
   - Design principles
   - Technology choices and why

3. **[Deployment](deployment.md)** - Running and deploying
   - Local development setup
   - Production deployment options
   - Docker, Fly.io, Railway guides
   - Performance and security

### Implementation Deep Dives

For understanding the code:

4. **[Backend Implementation](backend-implementation.md)** - FastAPI backend walkthrough
   - Complete code walkthrough with line numbers
   - Pydantic models
   - API endpoints
   - State management
   - Error handling
   - ~600 lines of detailed explanation

5. **[Frontend Implementation](frontend-implementation.md)** - React frontend walkthrough
   - Component structure
   - State management
   - SSE event parsing
   - Message rendering
   - Known issues and improvements

6. **[Claude SDK Integration](claude-sdk-integration.md)** - How we use the Claude Agent SDK
   - ClaudeAgentOptions configuration
   - Client lifecycle
   - Session management
   - Tool execution
   - Streaming implementation
   - Common issues

7. **[API Compatibility](api-compatibility.md)** - OpenAI Responses API format
   - Request/response formats
   - Streaming events (SSE)
   - Multi-turn conversations
   - Differences from OpenAI
   - Client examples (JavaScript, Python, cURL)

## 🎯 Quick Reference

### Need to...

**Understand how something works?**
→ Start with Architecture, then read the relevant implementation doc

**Deploy to production?**
→ Read Deployment guide

**Debug an issue?**
→ Search for "Common Issues" in implementation docs

**Learn Claude SDK usage?**
→ Read Claude SDK Integration

**Understand the API format?**
→ Read API Compatibility

**Query the agent about itself?**
→ Read Querying This Agent first!

## 🤖 For the Agent

If you are an instance of this agent:

- **These docs are your knowledge base about yourself**
- When users ask about implementation, architecture, or code:
  1. Search these docs for relevant information
  2. Read the actual source files mentioned
  3. Provide accurate answers with code snippets and line numbers
- See `CLAUDE.md` for detailed instructions on using these docs

## ⚠️ Maintaining Documentation

**Critical: Keep docs up-to-date!**

When changing code, update the relevant documentation:

- Backend changes → `backend-implementation.md`
- Frontend changes → `frontend-implementation.md`
- Architecture changes → `architecture.md`
- API changes → `api-compatibility.md`
- Deployment changes → `deployment.md`
- SDK usage changes → `claude-sdk-integration.md`

**See `CLAUDE.md` for the complete documentation update checklist.**

## 📊 Documentation Stats

- **Total docs**: 7 files (+ this index)
- **Total content**: ~20,000+ words
- **Code examples**: 100+ snippets
- **Line number references**: 50+ specific locations
- **Coverage**: 100% of major features

## 🔍 Search Tips

To find information quickly:

**Using grep** (command line):
```bash
grep -r "streaming" docs/
grep -r "ClaudeSDKClient" docs/
grep -r "SSE" docs/
```

**Using the agent** (chat interface):
```
"How does streaming work?"
"Where is session management implemented?"
"Show me the Claude SDK configuration"
```

**Using your editor**:
- VS Code: `Cmd/Ctrl+Shift+F` to search in folder
- Look for specific file paths, function names, or concepts

## 📝 Documentation Standards

Our docs follow these principles:

1. **Accurate**: Match current code exactly
2. **Detailed**: Include code snippets with line numbers
3. **Explanatory**: Explain "why" not just "what"
4. **Searchable**: Clear headings and keywords
5. **Practical**: Real examples and use cases
6. **Linked**: Reference related docs
7. **Maintained**: Updated with code changes

## 🚀 Using the Documentation

### For Developers

1. **Learning the codebase**: Read in order - Architecture → Backend → Frontend → SDK
2. **Making changes**: Read relevant impl doc first, update it after
3. **Debugging**: Search for error messages or concepts
4. **Contributing**: Use the doc checklist in `CLAUDE.md`

### For Users

1. **Getting started**: Read Deployment
2. **Understanding features**: Read Architecture
3. **API integration**: Read API Compatibility
4. **Asking questions**: Read Querying This Agent

### For the Agent (You!)

1. **User asks about implementation**: Search docs, read source, explain with code
2. **User asks how to do something**: Reference Deployment or Architecture
3. **User reports issue**: Check implementation docs for troubleshooting
4. **User asks about design**: Explain from Architecture doc

## 🔗 External References

Additional documentation outside this folder:

- `/CLAUDE.md` - Project overview and agent configuration
- `/README.md` - Quick project introduction
- `/reference/claude-agent-sdk.md` - Official SDK reference
- `/reference/openapi.documented.yml` - OpenAI API spec

## 💡 Tips for Best Results

**When reading documentation**:
- Don't skip the code examples
- Follow the line number references
- Check the source code when in doubt
- Look for "Common Issues" sections

**When asking the agent**:
- Be specific about what you want to know
- Ask for code examples
- Request file paths and line numbers
- Build on previous questions in conversation

**When updating documentation**:
- Use actual code snippets, not pseudocode
- Include file paths and line numbers
- Explain trade-offs and alternatives
- Add troubleshooting for known issues
- Test by asking the agent to verify

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [Anthropic Claude Documentation](https://docs.anthropic.com/)
- [OpenAI API Reference](https://platform.openai.com/docs/)
- [Server-Sent Events (SSE) Specification](https://html.spec.whatwg.org/multipage/server-sent-events.html)

## ❓ Questions?

If you can't find what you're looking for:

1. **Ask the agent**: It can search these docs for you
2. **Use grep**: Search all docs for keywords
3. **Read the source**: Code is the ultimate truth
4. **Update docs**: If you find gaps, fill them!

---

**Remember**: This documentation is a living system. Keep it current, and it will keep you informed!
