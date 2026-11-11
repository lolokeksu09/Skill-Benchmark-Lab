package dev.skilllab.ui;

import static androidx.test.espresso.Espresso.onView;
import static androidx.test.espresso.action.ViewActions.click;
import static androidx.test.espresso.assertion.ViewAssertions.matches;
import static androidx.test.espresso.matcher.ViewMatchers.withContentDescription;
import static androidx.test.espresso.matcher.ViewMatchers.withId;
import static androidx.test.espresso.matcher.ViewMatchers.withText;
import static org.junit.Assert.*;
import android.util.DisplayMetrics;
import android.view.View;
import androidx.test.ext.junit.rules.ActivityScenarioRule;
import androidx.test.ext.junit.runners.AndroidJUnit4;
import org.junit.Rule;
import org.junit.Test;
import org.junit.runner.RunWith;

@RunWith(AndroidJUnit4.class)
public class LabActivityTest {
  @Rule public ActivityScenarioRule<LabActivity> scenario = new ActivityScenarioRule<>(LabActivity.class);
  @Test public void headingAndSearchAreVisible() {
    onView(withId(LabActivity.TITLE)).check(matches(withText("Latest discussions")));
    onView(withId(LabActivity.SEARCH)).check(matches(withContentDescription("Search discussions")));
  }
  @Test public void bookmarkProvidesAccessibleState() {
    onView(withId(LabActivity.BOOKMARK)).check(matches(withContentDescription("Save discussion")));
    onView(withId(LabActivity.BOOKMARK)).perform(click());
    onView(withId(LabActivity.BOOKMARK)).check(matches(withContentDescription("Remove saved discussion")));
    scenario.getScenario().onActivity(activity -> assertTrue(activity.isSaved()));
  }
  @Test public void staleUpdateRestoresPreviousState() {
    scenario.getScenario().onActivity(LabActivity::simulateStaleResponseOnce);
    onView(withId(LabActivity.BOOKMARK)).perform(click());
    onView(withId(LabActivity.BOOKMARK)).check(matches(withContentDescription("Save discussion")));
    onView(withId(LabActivity.STATUS)).check(matches(withText("Could not update. Retry.")));
    scenario.getScenario().onActivity(activity -> assertFalse(activity.isSaved()));
    onView(withId(LabActivity.BOOKMARK)).perform(click());
    scenario.getScenario().onActivity(activity -> assertTrue(activity.isSaved()));
  }
  @Test public void touchTargetAndLayoutFitOnDevice() {
    scenario.getScenario().onActivity(activity -> {
      View b=activity.findViewById(LabActivity.BOOKMARK);
      View root=activity.findViewById(1000);
      DisplayMetrics m=activity.getResources().getDisplayMetrics();
      assertTrue("touch target width", b.getWidth() >= (int)(44*m.density));
      assertTrue("touch target height", b.getHeight() >= (int)(44*m.density));
      assertTrue("root fits screen", root.getWidth() <= m.widthPixels);
      assertNotNull(b.getContentDescription());
    });
  }
}
