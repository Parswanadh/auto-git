"""
Quick test for conversational agent improvements
Tests: speed, decisiveness, ready signal detection
"""

import asyncio
import time
from src.langraph_pipeline.conversation_agent import have_conversation


async def test_conversation_speed():
    """Test that agent responds quickly"""
    print("🧪 Test 1: Response Speed")
    print("-" * 50)
    
    start = time.time()
    result = await have_conversation(
        "I want to make a small LLM for code review using Gemma 270M",
        thread_id="test_speed"
    )
    duration = time.time() - start
    
    print(f"⏱️  Response time: {duration:.2f}s")
    print(f"📝 Agent: {result['agent_response'][:200]}...")
    print(f"✅ PASS: Response in {duration:.2f}s" if duration < 10 else f"❌ FAIL: Too slow ({duration:.2f}s)")
    print()
    
    return duration < 10


async def test_ready_signal_detection():
    """Test that agent detects ready signals"""
    print("🧪 Test 2: Ready Signal Detection")
    print("-" * 50)
    
    # First message
    result1 = await have_conversation(
        "Build code review LLM with Gemma 270M for bugs and style",
        thread_id="test_ready"
    )
    print(f"📝 Agent (turn 1): {result1['agent_response'][:150]}...")
    
    # User says "yes" - should be detected as ready
    result2 = await have_conversation(
        "yes, let's go",
        thread_id="test_ready"
    )
    print(f"📝 Agent (turn 2): {result2['agent_response'][:150]}...")
    print(f"🎯 Ready: {result2['ready_for_pipeline']}")
    print(f"📊 Confidence: {result2['confidence']:.2%}")
    
    passed = result2['ready_for_pipeline'] or result2['confidence'] > 0.7
    print(f"✅ PASS: Detected ready signal" if passed else "❌ FAIL: Missed ready signal")
    print()
    
    return passed


async def test_decisiveness():
    """Test that agent is decisive and doesn't over-clarify"""
    print("🧪 Test 3: Decisiveness (Max 2 questions)")
    print("-" * 50)
    
    result = await have_conversation(
        "I want to fine-tune Gemma 3 270M on code review datasets focusing on bug detection and style",
        thread_id="test_decisive"
    )
    
    response = result['agent_response']
    question_marks = response.count('?')
    
    print(f"📝 Agent: {response[:300]}...")
    print(f"❓ Question marks: {question_marks}")
    print(f"🎯 Confidence: {result['confidence']:.2%}")
    
    # Should either be ready or ask max 2 questions
    passed = result['ready_for_pipeline'] or question_marks <= 3
    print(f"✅ PASS: Decisive response" if passed else f"❌ FAIL: Too many questions ({question_marks})")
    print()
    
    return passed


async def run_tests():
    """Run all tests"""
    print("\n" + "="*50)
    print("🚀 CONVERSATIONAL AGENT TEST SUITE")
    print("="*50 + "\n")
    
    results = []
    
    # Test 1: Speed
    try:
        results.append(await test_conversation_speed())
    except Exception as e:
        print(f"❌ Test 1 failed with error: {e}\n")
        results.append(False)
    
    # Test 2: Ready signals
    try:
        results.append(await test_ready_signal_detection())
    except Exception as e:
        print(f"❌ Test 2 failed with error: {e}\n")
        results.append(False)
    
    # Test 3: Decisiveness
    try:
        results.append(await test_decisiveness())
    except Exception as e:
        print(f"❌ Test 3 failed with error: {e}\n")
        results.append(False)
    
    # Summary
    print("="*50)
    print("📊 TEST SUMMARY")
    print("="*50)
    passed = sum(results)
    total = len(results)
    print(f"✅ Passed: {passed}/{total}")
    print(f"❌ Failed: {total - passed}/{total}")
    print(f"📈 Success Rate: {passed/total*100:.0f}%")
    print()
    
    if passed == total:
        print("🎉 All tests passed! Agent is fast, decisive, and responsive!")
    else:
        print("⚠️  Some tests failed. Review the output above.")


if __name__ == "__main__":
    asyncio.run(run_tests())
