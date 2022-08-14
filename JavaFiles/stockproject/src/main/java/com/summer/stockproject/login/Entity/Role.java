package com.summer.stockproject.login.Entity;

import javax.persistence.*;
import java.io.Serializable;
import java.util.Objects;

@Entity
@Table(name="authorities")
public class Role  implements Serializable {


    @EmbeddedId
    private userrole userrole = new userrole();

    @ManyToOne
    @JoinColumn(name = "useremail", insertable = false, updatable = false)
    @org.hibernate.annotations.ForeignKey(name = "fk")
    private User user;

    public userrole getUserRole() {
        return userrole;
    }

    public void setUserRole(userrole userrole) {
        this.userrole = userrole;
    }
    public Role() {

    }
    public Role(userrole userrole) {
        this.userrole = userrole;
    }

    @Override
    public String toString() {
        return "Role{" +
                "userRole=" + userrole +
                '}';
    }
}
