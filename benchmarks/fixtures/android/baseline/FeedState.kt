package lab.fixture

data class FeedState(val unread: Int, val seenIds: Set<String> = emptySet())

fun markPostRead(state: FeedState, postId: String): FeedState =
    state.copy(unread = state.unread - 1, seenIds = state.seenIds + postId)
