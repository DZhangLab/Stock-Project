import java.sql.Timestamp;
import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.time.LocalDate;
import java.util.Date;

public class testmain {
    public static void main(String[]args) throws ParseException {

        Date test = new Date();
        Date test1 = new SimpleDateFormat("yyyy-MM-dd hh:mm:ss").parse("2011-01-01 15:00:00");
        Timestamp sqltime = new Timestamp(test1.getTime());
        System.out.println("etet " + sqltime);
    }
}
