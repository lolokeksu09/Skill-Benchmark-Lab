package lab.fixture

fun main() {
    val initial = FeedState(unread = 1)
    val once = markPostRead(initial, "post-1")
    val twice = markPostRead(once, "post-1")
    check(once.unread == 0) { "EXPECTED_FIXTURE_FAILURE: markPostRead should decrement once" }
    check(twice == once) { "EXPECTED_FIXTURE_FAILURE: markPostRead must be idempotent" }
    check(markPostRead(FeedState(unread = 0), "post-2").unread == 0) {
        "EXPECTED_FIXTURE_FAILURE: unread count cannot become negative"
    }
    println("REFERENCE_OK: Kotlin state contracts passed")
}
