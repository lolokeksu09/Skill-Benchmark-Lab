package dev.skilllab.ui;

import android.app.Activity;
import android.os.Bundle;
import android.graphics.Color;
import android.graphics.Typeface;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;

/** Native Android view fixture. No network or personal content. */
public final class LabActivity extends Activity {
    public static final int TITLE = 1001;
    public static final int SEARCH = 1002;
    public static final int BOOKMARK = 1003;
    public static final int STATUS = 1004;
    private boolean saved = false;
    private boolean rejectNextSave = false;
    private Button bookmark;
    private TextView status;

    private int dp(int v) { return Math.round(getResources().getDisplayMetrics().density * v); }
    private void updateBookmark() {
        bookmark.setText(saved ? "★" : "☆");
        bookmark.setContentDescription(saved ? "Remove saved discussion" : "Save discussion");
        bookmark.setSelected(saved);
    }
    public void simulateStaleResponseOnce() { rejectNextSave = true; }
    public boolean isSaved() { return saved; }

    @Override public void onCreate(Bundle b) {
        super.onCreate(b);
        LinearLayout main = new LinearLayout(this);
        main.setOrientation(LinearLayout.VERTICAL);
        main.setPadding(dp(20), dp(28), dp(20), dp(20));
        main.setBackgroundColor(Color.rgb(247, 247, 244));
        main.setId(1000);
        main.setFocusableInTouchMode(true);
        TextView title = new TextView(this);
        title.setId(TITLE); title.setText("Latest discussions");
        title.setTextSize(25); title.setTypeface(null, Typeface.BOLD);
        title.setTextColor(Color.rgb(20, 30, 41));
        main.addView(title,new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(64)));
        EditText search = new EditText(this);
        search.setId(SEARCH); search.setSingleLine(true);
        search.setHint("Search discussions");
        search.setContentDescription("Search discussions");
        search.setMinHeight(dp(48));
        main.addView(search,new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(56)));
        TextView description = new TextView(this);
        description.setText("Public discussion – a local fixture. Save what matters.");
        description.setTextColor(Color.rgb(55, 65, 78));
        description.setTextSize(16);
        description.setPadding(0,dp(24),0,dp(12));
        main.addView(description,new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        bookmark = new Button(this);
        bookmark.setId(BOOKMARK);
        bookmark.setMinWidth(dp(48));bookmark.setMinHeight(dp(48));
        updateBookmark();
        LinearLayout.LayoutParams buttonLayout = new LinearLayout.LayoutParams(dp(72), dp(52));
        main.addView(bookmark,buttonLayout);
        status = new TextView(this);
        status.setId(STATUS); status.setText("Ready");
        status.setTextSize(16); status.setTextColor(Color.rgb(45, 56, 70));
        status.setAccessibilityLiveRegion(View.ACCESSIBILITY_LIVE_REGION_POLITE);
        main.addView(status,new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(52)));
        bookmark.setOnClickListener(v -> {
            if (rejectNextSave) {
                rejectNextSave = false;
                status.setText("Could not update. Retry.");
                return; // rollback: keep original state
            }
            saved = !saved; updateBookmark();
            status.setText(saved ? "Discussion saved" : "Discussion removed");
        });
        setContentView(main);
    }
}
