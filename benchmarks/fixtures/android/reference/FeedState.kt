package lab.fixture

data class FeedState(val unread: Int, val seenIds: Set<String> = emptySet())

fun markPostRead(state: FeedState, postId: String): FeedState {
    if (postId in state.seenIds) return state
    return state.copy(unread = (state.unread - 1).coerceAtLeast(0), seenIds = state.seenIds + postId)
}
